"""
Web-friendly version of the parameter-extraction agent.

Same behaviour as the CLI script, but run_turn() RETURNS the model's reply and
the generated netlists instead of printing them, so an HTTP layer can hand
them straight to the client. Netlists still never go back through the model.
"""

import os
import datetime
from pathlib import Path

from dotenv import load_dotenv
from ollama import Client, ChatResponse

from agent.circuits import CIRCUIT_TOOLS

load_dotenv()

MODEL = "gpt-oss:120b-cloud"
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)
MAX_STEPS = 6  # safety cap on model <-> tool round trips per user turn

client = Client(
    host="https://ollama.com",
    headers={"Authorization": "Bearer " + os.environ.get("OLLAMA_API_KEY", "")},
)

available_functions = {fn.__name__: fn for fn in CIRCUIT_TOOLS}

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
- After a tool succeeds, briefly confirm what was generated and where it
  was saved. You will NOT see the actual circuit text - only a short status
  message - so don't try to describe or repeat its contents.
"""


def new_conversation() -> list:
    return [{"role": "system", "content": SYSTEM_PROMPT}]


def save_netlist(circuit_name: str, netlist: str) -> Path:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = OUTPUT_DIR / f"{circuit_name}_{timestamp}.txt"
    path.write_text(netlist)
    return path


def execute_tool_call(name: str, arguments: dict, generated: list) -> str:
    """Run a circuit function, append the full result to `generated` (for the
    API response), and return a SHORT status string for the model."""
    if name not in available_functions:
        return f"Error: no tool named '{name}' is available."

    try:
        netlist = available_functions[name](**arguments)
    except (ValueError, TypeError) as e:
        return f"Error calling {name} with {arguments}: {e}"

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
    return f"Generated '{name}' successfully. Saved to {path} ({line_count} lines)."


def run_turn(messages: list) -> tuple[str, list[dict]]:
    """Resolve one user turn. Returns (assistant_text, generated_circuits)."""
    generated: list[dict] = []
    replies: list[str] = []

    for _ in range(MAX_STEPS):
        response: ChatResponse = client.chat(
            model=MODEL,
            messages=messages,
            tools=list(available_functions.values()),
            think=True,
        )
        messages.append(response.message)

        if response.message.content:
            replies.append(response.message.content)

        if not response.message.tool_calls:
            break

        for tc in response.message.tool_calls:
            result = execute_tool_call(
                tc.function.name, tc.function.arguments, generated
            )
            messages.append(
                {"role": "tool", "tool_name": tc.function.name, "content": result}
            )
    else:
        replies.append("(Stopped: too many tool-call steps in one turn.)")

    return "\n\n".join(replies), generated