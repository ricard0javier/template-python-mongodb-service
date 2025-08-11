from src.examples.agent_with_mongodb_memory import invoke_agent


def main():
    print(invoke_agent("What is the weather in London?", "John", "123"))


if __name__ == "__main__":
    main()
