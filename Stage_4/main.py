from datetime import datetime

from langchain_core.messages import HumanMessage

from parking.pipeline import build_graph, ParkingState
from parking.services import sanitize_input_nl
from parking.services import auto_release_expired_reservations
from parking.database import get_connection


def run_interactive():
    """
    Run a continuous interactive session with the parking assistant.

    Workflow per turn:
        1. Sanitize user input.
        2. Prepend current date/time for context.
        3. Invoke the LangGraph pipeline.
        4. Display the latest AI message.
    """
    print("\nSchiphol Parking Assistant")
    print("Type 'exit' or 'quit' to stop.\n")

    react_graph = build_graph()

    state: ParkingState = {
        "messages": [],
        "data": {},
    }

    while True:
        user_input = input("\nYou: ").strip()
        user_input = sanitize_input_nl(user_input)

        if user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break

        now_str = datetime.now().strftime("%d-%m-%Y %H:%M")
        input_with_datetime = f"Today is {now_str}. {user_input}"

        state["messages"].append(HumanMessage(content=input_with_datetime))

        try:
            state = react_graph.invoke(state)
            print(f"\nAI: {state['messages'][-1].content}\n")
        except Exception as e:
            print(f"\nSystem error: {e}")
            break


if __name__ == "__main__":
    conn = get_connection()
    auto_release_expired_reservations(conn)
    conn.close()
    run_interactive()
