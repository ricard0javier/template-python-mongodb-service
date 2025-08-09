from src.persistence.mongodb import get_client
from langgraph.checkpoint.mongodb import MongoDBSaver


def get_mongodb_saver(collection_name: str, db_name: str):
    MongoDBSaver(
        client=get_client().client,
        checkpointCollectionName=collection_name,
        db_name=db_name,
    ),
