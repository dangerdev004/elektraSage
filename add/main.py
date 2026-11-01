"""
Command-line front end for the circuit design agent.

All of the agent's logic (system prompt, tool registry, cascade / parallel_sum, the fix-apply memory,
the code-written replies) lives in agent/service.py, which the web app also uses. This file only reads a line,
hands it to the service and prints what comes back, so the CLI and the app cannot drift apart.
"""

from agent.service import new_conversation, run_turn


def main() -> None:
    messages = new_conversation()
    print("Circuit agent ready. Describe a circuit, or type 'exit' to quit.")

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})
        try:
            text, generated = run_turn(messages)
        except Exception as e:                      # network / model errors should not end the session
            print(f"\nAgent: sorry, that turn failed ({type(e).__name__}: {e}).")
            messages.pop()
            continue

        for g in generated:
            print(f"\n--- Generated circuit ({g['circuit']}) ---")
            print(g["netlist"])
            print(f"--- Saved to {g['saved_to']} ---")
        if text:
            print(f"\nAgent: {text}")


if __name__ == "__main__":
    main()
