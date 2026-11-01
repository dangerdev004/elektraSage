"""
Web-friendly version of the parameter-extraction agent.

Same behaviour as the CLI script, but run_turn() RETURNS the model's reply and
the generated netlists instead of printing them, so an HTTP layer can hand
them straight to the client. Netlists still never go back through the model.
"""

import os
import re
import warnings
import contextvars
import copy
import datetime
from pathlib import Path

from dotenv import load_dotenv
from ollama import Client, ChatResponse

from agent.circuits import CIRCUIT_TOOLS
from agent.cascade.tool import INTERNAL, cascade, parallel_sum, render_number, render_single

load_dotenv()

MODEL = "gpt-oss:120b-cloud"
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)
MAX_STEPS = 6  # safety cap on model <-> tool round trips per user turn

client = Client(
    host="https://ollama.com",
    headers={"Authorization": "Bearer " + os.environ.get("OLLAMA_API_KEY", "")},
)

_CURRENT: contextvars.ContextVar = contextvars.ContextVar("current_conversation", default=None)


class Conversation(list):
    """The message list of one session, plus what code remembers between turns: the
    rebuild call for the buffer fix the last reply offered."""
    pending_fix: tuple | None = None
    pending_alt: tuple | None = None       # rebuild exactly as asked (undo the automatic buffers)


def apply_fix() -> str:
    """Apply the fix that the previous cascade or parallel_sum reply offered (added buffers, or a
    lower source amplitude for headroom).

    Call this with NO arguments when the user says things like "apply the fix", "yes, add the
    buffers" or "do the buffer fix" right after a reply that offered one. It rebuilds that same
    circuit with the fix; no parameters are needed because the code remembers them.
    """
    raise ValueError("apply_fix runs through execute_tool_call")


def build_without_buffers() -> str:
    """Rebuild the last circuit exactly as the user asked, without the voltage followers that
    code added automatically.

    Call this with NO arguments when the user says "build it without the buffers", "as I asked"
    or "undo the buffers" right after a reply that said buffers were added automatically.
    """
    raise ValueError("build_without_buffers runs through execute_tool_call")


available_functions = {fn.__name__: fn for fn in [*CIRCUIT_TOOLS, cascade, parallel_sum,
                                                   apply_fix, build_without_buffers]}

SYSTEM_PROMPT = """You are a circuit-parameter extraction assistant.

Your job is ONLY to figure out which circuit the user wants and extract the
parameters needed to generate it, then call the matching tool.

Rules:
- You can only generate circuits you have a tool for. If the user asks for
  something you don't have a tool for, tell them plainly that it isn't
  supported yet - do not guess or improvise a substitute.
- If the user's request is missing required parameters (e.g. "make me a
  lowpass filter" with no cutoff frequency), ask them for exactly the
  missing values. Do not call a tool with guessed or placeholder numbers.
- Once you have every required parameter, call the tool. Don't ask for
  confirmation first if you already have everything you need.
- If the user wants two signal paths in PARALLEL whose outputs are then summed,
  added or mixed (e.g. "a low-pass and a high-pass in parallel, summed"), call
  `parallel_sum` ONCE with the two paths. Each path is an ordered list of
  circuits. Use `cascade` for a single chain. Do not write your own summary: the
  reply is written by code.
- If the user asks for a buffer or voltage follower between stages, include
  `voltage_follower` as a stage of the `cascade` call, in that position.
- When the user asks to apply, accept or do the buffer fix a reply just offered, call
  `apply_fix` with no arguments. Do not rebuild the arguments yourself.
- When a reply says buffers were added automatically and the user wants the circuit exactly
  as asked, call `build_without_buffers` with no arguments.
- Call the tool for EVERY circuit request, even if the same circuit was built
  earlier in this conversation. Never answer by pointing to an earlier circuit
  or file: the user needs a fresh circuit with this reply.
- If the user wants circuits chained or cascaded (e.g. "a high-pass filter,
  then a low-pass filter, then an inverting amplifier"), call the `cascade`
  tool ONCE with every stage in order instead of calling the circuit tools
  one by one. You choose the order from the request and extract each stage's
  parameters from it; ask for any that are missing, never invent values.
  Restate the plan in one line in your reply, e.g. "Cascade: RC high-pass
  100 Hz -> RC low-pass 5 kHz -> inverting amp x10".
- After `cascade` succeeds you also receive a fact sheet containing a
  code-computed block ("Computed response of the whole chain") and "Flags".
  Report those figures exactly as given: never recompute, re-round or
  contradict them, and never use a stage's own default source amplitude for the
  chain (the chain is driven by the source named in the sheet). Explain each
  flag in plain words and suggest the fix it names (for loading between
  stages, a unity-gain buffer at that junction). If the sheet says NOT
  ANALYSED, tell the user the response could not be checked. Never claim the
  circuit has been verified.
- Only offer fixes you can really perform with your tools; the fact sheet says
  which exist. When it lists none, say plainly that the fix is not available
  automatically yet and describe it as a manual change. Report the sheet's
  "What-if" figures as the expected result of the fix and claim no other
  outcome; if the sheet notes reduced headroom after the fix, say so.
- Only ever ask the user for parameters that have no default value (the tool
  descriptions mark them REQUIRED). Never ask about optional parameters - leave
  them out so their defaults apply - and never ask for a source amplitude or
  frequency for any stage after the first in a cascade.
- After a tool succeeds, briefly confirm what was generated and where it
  was saved. You will NOT see the actual circuit text - only a short status
  message - so don't try to describe or repeat its contents.
"""


def new_conversation() -> list:
    return Conversation([{"role": "system", "content": SYSTEM_PROMPT}])


def save_netlist(circuit_name: str, netlist: str) -> Path:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = OUTPUT_DIR / f"{circuit_name}_{timestamp}.txt"
    path.write_text(netlist)
    return path


def execute_tool_call(name: str, arguments: dict, generated: list, canned: list | None = None) -> str:
    """Run a circuit function, append the full result to `generated` (for the
    API response), and return a SHORT status string for the model.

    On success a reply written by code (no model prose) is appended to `canned`
    when that list is supplied; run_turn uses it verbatim."""
    if name not in available_functions:
        return f"Error: no tool named '{name}' is available."

    conv = _CURRENT.get()
    from_memory = name in ("apply_fix", "build_without_buffers")
    if from_memory:
        pending = getattr(conv, "pending_fix" if name == "apply_fix" else "pending_alt", None)
        if not pending:
            return ("Error: there is nothing to "
                    + ("apply" if name == "apply_fix" else "undo")
                    + " from the last circuit reply. Tell the user, and ask what they want built.")
        name, arguments = pending[0], copy.deepcopy(pending[1])

    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            fn = INTERNAL.get(name) if from_memory else None     # remembered calls may use code-only switches
            result = (fn or available_functions[name])(**arguments)
    except (ValueError, TypeError) as e:
        return f"Error calling {name} with {arguments}: {e}"
    warns = [str(w.message) for w in caught]

    # Tools may return text, (text, note) - the 555 generators and cascade -
    # or a plain number (resistors_approximation etc.).
    note = None
    netlist = result
    if isinstance(result, tuple):
        netlist, note = result
    if not isinstance(netlist, str):
        if canned is not None:
            canned.append(render_number(name, arguments, netlist))
        return f"{name}({arguments}) returned: {netlist}"

    if isinstance(conv, Conversation):          # remember (or clear) the fix this reply offers
        conv.pending_fix = getattr(note, "fix_call", None)
        conv.pending_alt = getattr(note, "alt_call", None)

    path = save_netlist(name, netlist)
    line_count = netlist.count("\n") + 1

    generated.append(
        {
            "circuit": name,
            "arguments": arguments,
            "saved_to": str(path),
            "netlist": netlist,
        }
    )
    if canned is not None:
        # cascade supplies its own reply (with the computed chain analysis); every other
        # circuit gets the single-circuit reply.
        body = getattr(note, "reply", "") or render_single(name, arguments, netlist, note, warns)
        canned.append(f"{body}\n\nSaved to `{path}`.")
    status = f"Generated '{name}' successfully. Saved to {path} ({line_count} lines)."
    return status + ("\n" + note if note else "")


# A reply that says a circuit was produced. Used only to catch the model claiming a
# build in a turn where no circuit was actually generated.
_CLAIM = re.compile(
    r"\b(?:has|have|had)(?: \w+)? been (?:generated|built|created|produced)\b"
    r"|\balready (?:generated|built|created|produced)\b"
    r"|\b(?:is|are|was) saved (?:as|at|to|in)\b"
    r"|\bhere(?:'s| is| are) (?:your|the)\b"
    r"|\bi(?:'ve| have) (?:generated|built|created|produced)\b"
    r"|\b(?:generated|built|created|produced) (?:your|the)\b", re.I)

NUDGE = ("(system note) You did not call any tool in your last reply, so no circuit was "
         "produced. If the user asked for a circuit, call the appropriate tool now. "
         "Otherwise answer without saying a circuit was generated.")

NO_CIRCUIT_WARNING = ("Note: no circuit was produced in this turn (no tool ran successfully). "
                      "Ignore any statement above that one was generated.")


def run_turn(messages: list) -> tuple[str, list[dict]]:
    """Resolve one user turn. Returns (assistant_text, generated_circuits)."""
    token = _CURRENT.set(messages)
    try:
        return _run_turn(messages)
    finally:
        _CURRENT.reset(token)


def _run_turn(messages: list) -> tuple[str, list[dict]]:
    generated: list[dict] = []
    replies: list[str] = []
    tools_called = False       # did the model call any tool this turn?
    nudged = False             # nudge at most once per turn
    kept: list[str] = []       # code replies from calls whose sibling calls failed
    nudge = None               # the nudge message while it is pending

    for _ in range(MAX_STEPS):
        response: ChatResponse = client.chat(
            model=MODEL,
            messages=messages,
            tools=list(available_functions.values()),
            think=True,
        )
        if nudge is not None:                  # keep the nudge out of the history
            messages.remove(nudge)
            nudge = None
        messages.append(response.message)

        if response.message.content:
            replies.append(response.message.content)

        if not response.message.tool_calls:
            claims = bool(response.message.content and _CLAIM.search(response.message.content))
            if claims and not generated:
                if not tools_called and not nudged:
                    # A: first claim with no tool call at all -> drop it and ask once more.
                    messages.pop()
                    replies.pop()
                    nudge = {"role": "user", "content": NUDGE}
                    messages.append(nudge)
                    nudged = True
                    continue
                # B: still claiming (or a tool failed): keep the text, add the warning.
                replies.append(NO_CIRCUIT_WARNING)
            break

        tools_called = True
        canned_step: list[str] = []
        all_canned = True
        for tc in response.message.tool_calls:
            before = len(canned_step)
            result = execute_tool_call(
                tc.function.name, tc.function.arguments, generated, canned_step
            )
            messages.append(
                {"role": "tool", "tool_name": tc.function.name, "content": result}
            )
            if len(canned_step) == before:          # error or nothing to say: the model replies
                all_canned = False

        if not all_canned:
            kept.extend(canned_step)                 # never lose a code-written reply
            continue

        if canned_step and all_canned:
            # Code-written reply: drop any model prose from this step and finish.
            if response.message.content:
                replies.pop()
            text = "\n\n".join(canned_step)
            replies.append(text)
            messages.append({"role": "assistant", "content": text})
            break
    else:
        replies.append("(Stopped: too many tool-call steps in one turn.)")

    return "\n\n".join(kept + replies), generated