from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI


def agent_chatbot(chatbot_tools, chatbot_memory):
    """
        Create and return a LangChain tool-calling chatbot agent for airport parking.

        This function sets up a ChatOpenAI LLM agent that:
        - Uses provided tools to answer user questions about parking reservations, availability, and prices.
        - Does not modify the database; only validates, informs, or assists with reservation operations.
        - Remembers conversation context via chatbot_memory for clearer interactions.

        Parameters:
            chatbot_tools (list): List of tools the agent can use to query or validate data.
            chatbot_memory: Memory object to store past conversation context.

        Returns:
            AgentExecutor: Configured LangChain agent executor ready to handle chat input.
        """


    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a helpful and factual assistant managing airport parking at Schiphol.\n"
        "- Never make up information about reservations, availability, or prices.\n"
        "- Always use the provided tools to answer user questions about the database.\n"
        "- You can remember past conversation context for clarity, but all factual data must come from tools.\n"
        "- You can assist with validating reservations, cancellations, changes, and providing general information . But you can t make any changes in the database"
        ),

        # Memory goes here
        MessagesPlaceholder(variable_name="chat_history"),

        ("human", "{input}"),

        # Required for tool agents
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0)
    agent = create_tool_calling_agent(
        llm, chatbot_tools, prompt)

    # -----------------------
    # Executor
    # -----------------------

    agent_executor = AgentExecutor(
        agent=agent,
        tools=chatbot_tools,
        verbose=True,
        memory=chatbot_memory,
        return_intermediate_steps=True# ✅ add this line
    )


    return agent_executor