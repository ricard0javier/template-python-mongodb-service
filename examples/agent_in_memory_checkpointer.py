import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver
from openai import BaseModel
from langgraph.prebuilt.chat_agent_executor import AgentState
from langchain_core.messages import AnyMessage
from langgraph.runtime import get_runtime

from src.agent.model import ContextSchema
from src.agent.tools.address_tools import get_address
from src.agent.tools.weather_tools import get_weather
from src.config import OPENAI_API_KEY, OPENAI_MODEL_NAME

# Load environment variables from .env file
load_dotenv()


def prompt(state: AgentState) -> list[AnyMessage]:
    runtime = get_runtime(ContextSchema)
    system_msg = (
        f"You are a helpful assistant. Address the user as {runtime.context.user_name}."
    )
    return [{"role": "system", "content": system_msg}] + state["messages"]


class AgentResponse(BaseModel):
    weather_conditions: str
    temperature: float
    address: str


agent = create_react_agent(
    model=init_chat_model(
        model=OPENAI_MODEL_NAME,
        api_key=OPENAI_API_KEY,
        temperature=0.0,
        # max_tokens=1000,
    ),
    # the AI model will be queried to choose which tool to use based on the user's request
    tools=[get_weather, get_address],
    prompt=prompt,
    context_schema=ContextSchema,
    # the agent will save its state in memory
    checkpointer=InMemorySaver(),
    # Structured output requires an additional call to the LLM to format the response according to the schema.
    response_format=AgentResponse,
)


def invoke_agent(user_message: str, user_name: str, thread_id: str):
    return agent.invoke(
        {"messages": [{"role": "user", "content": user_message}]},
        context=ContextSchema(user_name=user_name),
        config={"thread_id": thread_id},
    )
