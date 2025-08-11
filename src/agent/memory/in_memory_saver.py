from langgraph.checkpoint.memory import InMemorySaver, InMemoryStore


def get_in_memory_saver():
    return InMemorySaver()


def get_in_memory_store():
    return InMemoryStore()
