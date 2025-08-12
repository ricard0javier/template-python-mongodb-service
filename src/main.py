from src.examples.agent_with_mongodb_memory import invoke_agent


def get_result(sender_name: str, user_message: str, receiver_name: str):
    print(f"👤 {sender_name}: {user_message}")

    # get user type
    if sender_name == "Ricardo":
        sender_type = "owner"
    else:
        sender_type = "contact"

    # invoke agent
    result = invoke_agent("010", sender_type, sender_name, receiver_name, user_message)
    if result is None:
        return

    # print result
    print(f"🤖 Bot: {result['messages'][-1].content}")
    return result


def main():
    # get_result("Paula", "Hey, how are you?", "Ricardo")
    # # bot responds
    # get_result("Paula", "Do you know if MongoDB can perform vector search?", "Ricardo")
    # # bot responds
    # get_result("Paula", "How can I deploy it locally to play with it?", "Ricardo")
    # # bot responds
    # get_result(
    #     "Ricardo",
    #     "Ask me about MongoDB any time, but I don't want to talk about SQL, the world is already too messy",
    #     "Paula",
    # )
    # # bot responds
    # get_result("Paula", "But what about SQL?", "Ricardo")

    get_result("Paula", "So I can do that search, what do I need to do?", "Ricardo")


if __name__ == "__main__":
    main()
