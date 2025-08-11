from langchain_core.runnables import RunnableConfig
from langgraph.config import get_store

from src.agent.model import ContextSchema


def get_weather(
    city: str, user: str, config: RunnableConfig, context: ContextSchema
) -> str:
    """Get weather for a given city."""
    store = get_store()
    user_id = context.user_name
    print(f"user_id: {user_id}")
    store.put(
        ("weather_requests",),
        user_id,
        {
            "interested_in": city,
            "weather": "sunny",
        },
    )
    return f"It's always sunny in {city}!"
