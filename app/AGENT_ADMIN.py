from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import MessagesPlaceholder, ChatPromptTemplate
from langchain_openai import ChatOpenAI
from INITIALIZATION_sqlite_db import get_sqlite_connection

conn = get_sqlite_connection()


def agent_admin(admin_tools, admin_memory):
    """
       Create and return a LangChain admin agent for reviewing reservation requests.

       This function sets up a ChatOpenAI LLM agent that:
       - Reviews reservation-related requests sent by the chatbot agent before any changes are applied to the database.
       - Acts as a human administrator who approves or rejects requests based on system rules, database constraints, and behavioral policies.
       - Uses provided tools to validate requests, such as checking car reservation history, advance booking limits,  reservation duration and
       if there are any spots available to make a reservation or to change a reservation.

       Parameters:
           admin_tools (list): List of administrative tools the agent can call to validate requests.
           admin_memory: Memory object to store past conversation context.

       Returns:
           AgentExecutor: Configured LangChain admin agent executor ready to review reservation requests.
       """

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                f"""
You are the administrator of Schiphol Airport Parking.

Your role is to review reservation-related requests sent by the chatbot agent before any change is applied to the database. 
You act as a human reviewer who ensures that reservations follow system rules, database constraints, and behavioral policies.

You must decide whether to: "APPROVE" or "REJECT" the request.

Your review must follow these steps:

1. Understand the reservation request.
2. Review conversation memory for suspicious behavior.
3. Apply administrative judgment using these tools  MAKING A RESERVATION:
   - check_car_reservation_history: ensures a car does not have too many active reservations
   - check_advance_booking: ensures reservations are not too far in advance
   - check_reservation_length: ensures reservations are within allowed duration limits

Always call these tools as appropriate before making a final decision. Output a clear decision with reason if rejected.
"""
            ),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
    )

    agent = create_tool_calling_agent(
        llm,
        admin_tools,
        prompt,
    )

    admin = AgentExecutor(
        agent=agent,
        tools=admin_tools,
        verbose=True,
        memory=admin_memory,
        return_intermediate_steps=True
    )

    return admin