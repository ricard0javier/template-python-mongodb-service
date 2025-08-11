from persistence.mongodb import get_client
from langgraph.checkpoint.mongodb import MongoDBSaver
from langgraph.store.mongodb import MongoDBStore


def get_mongodb_saver(collection_name: str, db_name: str):
    MongoDBSaver(
        client=get_client().client,
        checkpointCollectionName=collection_name,
        db_name=db_name,
    ),


def get_mongodb_store(collection_name: str, db_name: str):
    client = get_client().client
    db = client[db_name]
    collection = db[collection_name]

    return MongoDBStore(
        collection=collection,
        ttl_config={
            "refresh_on_read": True,
            "default_ttl": 60 * 24 * 7,  # 7 days in minutes
        },
        # Add semantic search capabilities with vector indexing
        index_config={
            "dims": 1536,  # OpenAI text-embedding-ada-002 dimensions
            "embed": "openai:text-embedding-3-small",  # Use OpenAI embeddings
            "fields": ["$"],  # Index the main content
            "name": "store_vector_index",
            "relevance_score_fn": "cosine",
            "embedding_key": "store_embedding",
            "filters": ["namespace", "updated_at"],
        },
    )
