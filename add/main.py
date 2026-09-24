"""
Parameter-extraction agent for the circuit design pipeline.

Scope (per project design): this agent ONLY extracts parameters from the
user's request and calls the matching circuit-generation tool. It does not
control simulation, educational-resource generation, or anything else
downstream in the pipeline.

Flow:
  - User describes a circuit, with or without full parameters.
  - The model decides whether it has enough info to call a tool.
  - If not, it asks the user a follow-up question directly (no tool call).
  - If yes, it calls the matching function from agent.circuits.
  - The generated netlist is saved to disk and shown to the user directly
    (NOT relayed back through the model - see README/design notes on why).
"""

import os
import datetime
from pathlib import Path

from ollama import Client, ChatResponse

from agent.circuits import CIRCUIT_TOOLS

from dotenv import load_dotenv
load_dotenv()

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

MODEL = "gpt-oss:120b-cloud"
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

client = Client(
    host="https://ollama.com",
    headers={"Authorization": "Bearer " + os.environ.get("OLLAMA_API_KEY", "")},
)

# Build {function_name: callable} from the registry - add a new circuit by
# adding it to CIRCUIT_TOOLS in agent/circuits/__init__.py, nothing here
# needs to change.
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


# ---------------------------------------------------------------------------
# Tool execution
# ---------------------------------------------------------------------------

def save_netlist(circuit_name: str, netlist: str) -> Path:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"{circuit_name}_{timestamp}.txt"
    path.write_text(netlist)
    return path


def execute_tool_call(name: str, arguments: dict) -> str:
    """Run a circuit function and return a SHORT status string for the model.

    The full netlist is written to disk and printed for the user directly -
    it never goes back into the message history (see module docstring).
    """
    if name not in available_functions:
        return f"Error: no tool named '{name}' is available."

    try:
        netlist = available_functions[name](**arguments)
    except (ValueError, TypeError) as e:
        return f"Error calling {name} with {arguments}: {e}"

    path = save_netlist(name, netlist)
    line_count = netlist.count("\n") + 1

    print(f"\n--- Generated circuit ({name}) ---")
    print(netlist)
    print(f"--- Saved to {path} ---\n")

    return f"Generated '{name}' successfully. Saved to {path} ({line_count} lines)."


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

def run_turn(messages: list) -> None:
    """Resolve one user turn: keep calling the model/tools until the model
    produces a plain response with no further tool calls."""
    while True:
        response: ChatResponse = client.chat(
            model=MODEL,
            messages=messages,
            tools=list(available_functions.values()),
            think=True,
        )
        messages.append(response.message)

        if response.message.content:
            print(f"\nAgent: {response.message.content}")

        if not response.message.tool_calls:
            break

        for tc in response.message.tool_calls:
            result = execute_tool_call(tc.function.name, tc.function.arguments)
            messages.append(
                {"role": "tool", "tool_name": tc.function.name, "content": result}
            )
        # loop again so the model can react to the tool result(s)


def main() -> None:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    print("Circuit agent ready. Describe a circuit, or type 'exit' to quit.")

    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})
        run_turn(messages)


if __name__ == "__main__":
    main()
