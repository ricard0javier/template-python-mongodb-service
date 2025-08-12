from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import AnyMessage
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState

from src.agent.memory.mongodb_saver import get_mongodb_saver, get_mongodb_store
from src.agent.model import ContextSchema
from src.config import OPENAI_API_KEY, OPENAI_MODEL_NAME

# Load environment variables from .env file
load_dotenv()


def prompt(state: AgentState) -> list[AnyMessage]:
    system_msg = """
    Act as a helpful Personal Assistant that is answering messages and acting on behalf of the owner.
    - You have to respond like if you were the owner.
    - You should use the same style as the owner to write your responses.
    - Generate short answers, max 10 words
    - Given the history of the conversation, you should identify constraints or rules that the owner has set.
    - If the owner has set a rule, you should follow it.
    - When the owner responds, your output should be empty.
    """

    return [{"role": "system", "content": system_msg}] + state["messages"]


agent = create_react_agent(
    model=init_chat_model(
        model=OPENAI_MODEL_NAME, api_key=OPENAI_API_KEY, temperature=0.0
    ),
    # the AI model will be queried to choose which tool to use based on the user's request
    tools=[],
    prompt=prompt,
    context_schema=ContextSchema,
    # the agent will save its state in memory
    checkpointer=get_mongodb_saver(
        collection_name="agent_checkpoints", db_name="playground"
    ),
    # requires MongoDB Atlas Vector Search or Atlas CLI
    store=get_mongodb_store(collection_name="agent_store", db_name="playground"),
)


def invoke_agent(
    thread_id: str,
    sender_type: str,
    sender_name: str,
    receiver_name: str,
    user_message: str,
):
    # Persist owner messages without invoking the LLM
    if sender_type == "owner":
        agent.update_state(
            {"configurable": {"thread_id": thread_id}},
            {
                "messages": [
                    {
                        "role": "user",
                        "content": user_message,
                        "sender_name": sender_name,
                        "sender_type": sender_type,
                        "receiver_name": receiver_name,
                    }
                ]
            },
        )
        return None

    return agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": user_message,
                    "sender_name": sender_name,
                    "sender_type": sender_type,
                    "receiver_name": receiver_name,
                }
            ]
        },
        context=ContextSchema(
            sender_name=sender_name,
            sender_type=sender_type,
            receiver_name=receiver_name,
        ),
        config={"configurable": {"thread_id": thread_id}},
    )
