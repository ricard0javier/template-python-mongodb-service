from pymongo import MongoClient
from src.config import MONGODB_URI


def main():
    """
    Main function for the Python project template.
    This function can be used as an entry point for your application.
    """
    print("===== Starting MongoDB Service Template =====")
    client = MongoClient(MONGODB_URI)
    db = client["playground"]
    testCollection = db["test"]
    testCollection.insert_one({"name": "John", "age": 30})
    cursor = testCollection.find({"name": "John"})
    print(list(cursor))


if __name__ == "__main__":
    main()
