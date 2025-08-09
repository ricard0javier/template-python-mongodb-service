"""
MongoDB client implementation with best practices.

This module provides a simple yet robust MongoDB client with connection pooling,
error handling, and common database operations.
"""

import logging
from typing import Any, Dict, List, Optional, Union
from contextlib import contextmanager

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import (
    ConnectionFailure,
    ServerSelectionTimeoutError,
    DuplicateKeyError,
    BulkWriteError,
)
from bson import ObjectId
from bson.errors import InvalidId

from ..config import (
    MONGODB_URI,
    MONGODB_DATABASE,
    MONGODB_MAX_POOL_SIZE,
    MONGODB_MIN_POOL_SIZE,
    MONGODB_MAX_IDLE_TIME_MS,
    MONGODB_CONNECT_TIMEOUT_MS,
    MONGODB_SERVER_SELECTION_TIMEOUT_MS,
    MONGODB_RETRY_WRITES,
    MONGODB_RETRY_READS,
)

# Set up logging
logger = logging.getLogger(__name__)


class MongoDBClient:
    """
    A MongoDB client wrapper that provides connection management and common operations.

    This client follows best practices including:
    - Connection pooling
    - Proper error handling
    - Automatic retries
    - Context management for transactions
    - Type hints for better IDE support
    """

    def __init__(self, uri: Optional[str] = None, database_name: Optional[str] = None):
        """
        Initialize the MongoDB client.

        Args:
            uri: MongoDB connection URI. If None, uses MONGODB_URI from config.
            database_name: Name of the database. If None, uses MONGODB_DATABASE from config.
        """
        self.uri = uri or MONGODB_URI
        self.database_name = database_name or MONGODB_DATABASE
        self._client: Optional[MongoClient] = None
        self._database: Optional[Database] = None

    def connect(self) -> None:
        """Establish connection to MongoDB with optimized settings."""
        try:
            logger.info(f"Connecting to MongoDB at {self.uri}")

            self._client = MongoClient(
                self.uri,
                maxPoolSize=MONGODB_MAX_POOL_SIZE,
                minPoolSize=MONGODB_MIN_POOL_SIZE,
                maxIdleTimeMS=MONGODB_MAX_IDLE_TIME_MS,
                connectTimeoutMS=MONGODB_CONNECT_TIMEOUT_MS,
                serverSelectionTimeoutMS=MONGODB_SERVER_SELECTION_TIMEOUT_MS,
                retryWrites=MONGODB_RETRY_WRITES,
                retryReads=MONGODB_RETRY_READS,
                # Additional production-ready settings
                maxConnecting=2,  # Limit concurrent connection attempts
                heartbeatFrequencyMS=10000,  # Check server status every 10s
                compressors="snappy,zlib",  # Enable compression
            )

            # Test the connection
            self._client.admin.command("ping")
            self._database = self._client[self.database_name]

            logger.info(
                f"Successfully connected to MongoDB database: {self.database_name}"
            )

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {e}")
            raise

    def disconnect(self) -> None:
        """Close the MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._database = None
            logger.info("Disconnected from MongoDB")

    @property
    def client(self) -> MongoClient:
        """Get the MongoDB client, connecting if necessary."""
        if self._client is None:
            self.connect()
        return self._client

    @property
    def database(self) -> Database:
        """Get the MongoDB database, connecting if necessary."""
        if self._database is None:
            self.connect()
        return self._database

    def get_collection(self, collection_name: str) -> Collection:
        """
        Get a MongoDB collection.

        Args:
            collection_name: Name of the collection

        Returns:
            MongoDB collection object
        """
        return self.database[collection_name]

    # CRUD Operations

    def insert_one(
        self, collection_name: str, document: Dict[str, Any]
    ) -> Optional[ObjectId]:
        """
        Insert a single document into a collection.

        Args:
            collection_name: Name of the collection
            document: Document to insert

        Returns:
            Inserted document's ObjectId or None if failed
        """
        try:
            collection = self.get_collection(collection_name)
            result = collection.insert_one(document)
            logger.debug(f"Inserted document with ID: {result.inserted_id}")
            return result.inserted_id
        except DuplicateKeyError as e:
            logger.warning(f"Duplicate key error inserting document: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inserting document: {e}")
            raise

    def insert_many(
        self, collection_name: str, documents: List[Dict[str, Any]]
    ) -> List[ObjectId]:
        """
        Insert multiple documents into a collection.

        Args:
            collection_name: Name of the collection
            documents: List of documents to insert

        Returns:
            List of inserted document ObjectIds
        """
        try:
            collection = self.get_collection(collection_name)
            result = collection.insert_many(
                documents, ordered=False
            )  # Continue on error
            logger.debug(f"Inserted {len(result.inserted_ids)} documents")
            return result.inserted_ids
        except BulkWriteError as e:
            logger.warning(
                f"Bulk write error - some documents may have been inserted: {e}"
            )
            # Return the IDs that were successfully inserted
            return [
                wr.upserted_id
                for wr in e.details.get("writeErrors", [])
                if wr.upserted_id
            ]
        except Exception as e:
            logger.error(f"Error inserting documents: {e}")
            raise

    def find_one(
        self,
        collection_name: str,
        filter_dict: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Find a single document in a collection.

        Args:
            collection_name: Name of the collection
            filter_dict: Query filter
            projection: Fields to include/exclude in the result

        Returns:
            Found document or None
        """
        try:
            collection = self.get_collection(collection_name)
            return collection.find_one(filter_dict, projection)
        except Exception as e:
            logger.error(f"Error finding document: {e}")
            raise

    def find_many(
        self,
        collection_name: str,
        filter_dict: Dict[str, Any] = None,
        projection: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        sort: Optional[List[tuple]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find multiple documents in a collection.

        Args:
            collection_name: Name of the collection
            filter_dict: Query filter (empty dict for all documents)
            projection: Fields to include/exclude in the result
            limit: Maximum number of documents to return
            sort: List of (field, direction) tuples for sorting

        Returns:
            List of found documents
        """
        try:
            collection = self.get_collection(collection_name)
            cursor = collection.find(filter_dict or {}, projection)

            if sort:
                cursor = cursor.sort(sort)
            if limit:
                cursor = cursor.limit(limit)

            return list(cursor)
        except Exception as e:
            logger.error(f"Error finding documents: {e}")
            raise

    def update_one(
        self,
        collection_name: str,
        filter_dict: Dict[str, Any],
        update_dict: Dict[str, Any],
        upsert: bool = False,
    ) -> int:
        """
        Update a single document in a collection.

        Args:
            collection_name: Name of the collection
            filter_dict: Query filter
            update_dict: Update operations
            upsert: Create document if it doesn't exist

        Returns:
            Number of documents modified
        """
        try:
            collection = self.get_collection(collection_name)
            result = collection.update_one(filter_dict, update_dict, upsert=upsert)
            logger.debug(f"Modified {result.modified_count} document(s)")
            return result.modified_count
        except Exception as e:
            logger.error(f"Error updating document: {e}")
            raise

    def update_many(
        self,
        collection_name: str,
        filter_dict: Dict[str, Any],
        update_dict: Dict[str, Any],
        upsert: bool = False,
    ) -> int:
        """
        Update multiple documents in a collection.

        Args:
            collection_name: Name of the collection
            filter_dict: Query filter
            update_dict: Update operations
            upsert: Create documents if they don't exist

        Returns:
            Number of documents modified
        """
        try:
            collection = self.get_collection(collection_name)
            result = collection.update_many(filter_dict, update_dict, upsert=upsert)
            logger.debug(f"Modified {result.modified_count} document(s)")
            return result.modified_count
        except Exception as e:
            logger.error(f"Error updating documents: {e}")
            raise

    def delete_one(self, collection_name: str, filter_dict: Dict[str, Any]) -> int:
        """
        Delete a single document from a collection.

        Args:
            collection_name: Name of the collection
            filter_dict: Query filter

        Returns:
            Number of documents deleted
        """
        try:
            collection = self.get_collection(collection_name)
            result = collection.delete_one(filter_dict)
            logger.debug(f"Deleted {result.deleted_count} document(s)")
            return result.deleted_count
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            raise

    def delete_many(self, collection_name: str, filter_dict: Dict[str, Any]) -> int:
        """
        Delete multiple documents from a collection.

        Args:
            collection_name: Name of the collection
            filter_dict: Query filter

        Returns:
            Number of documents deleted
        """
        try:
            collection = self.get_collection(collection_name)
            result = collection.delete_many(filter_dict)
            logger.debug(f"Deleted {result.deleted_count} document(s)")
            return result.deleted_count
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            raise

    def count_documents(
        self, collection_name: str, filter_dict: Dict[str, Any] = None
    ) -> int:
        """
        Count documents in a collection.

        Args:
            collection_name: Name of the collection
            filter_dict: Query filter (empty dict for all documents)

        Returns:
            Number of documents matching the filter
        """
        try:
            collection = self.get_collection(collection_name)
            return collection.count_documents(filter_dict or {})
        except Exception as e:
            logger.error(f"Error counting documents: {e}")
            raise

    def aggregate(
        self, collection_name: str, pipeline: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Run an aggregation pipeline on a collection.

        Args:
            collection_name: Name of the collection
            pipeline: Aggregation pipeline stages

        Returns:
            List of aggregation results
        """
        try:
            collection = self.get_collection(collection_name)
            return list(collection.aggregate(pipeline))
        except Exception as e:
            logger.error(f"Error running aggregation: {e}")
            raise

    @contextmanager
    def transaction(self):
        """
        Context manager for MongoDB transactions.

        Usage:
            with client.transaction():
                client.insert_one("collection1", {"data": "value1"})
                client.update_one("collection2", {"_id": id}, {"$set": {"status": "updated"}})
        """
        if not self._client:
            self.connect()

        session = self._client.start_session()
        try:
            with session.start_transaction():
                yield session
        except Exception:
            logger.error("Transaction aborted due to error")
            raise
        finally:
            session.end_session()

    def create_index(
        self,
        collection_name: str,
        keys: Union[str, List[tuple]],
        unique: bool = False,
        background: bool = True,
    ) -> str:
        """
        Create an index on a collection.

        Args:
            collection_name: Name of the collection
            keys: Field(s) to index or list of (field, direction) tuples
            unique: Whether the index should enforce uniqueness
            background: Whether to build the index in the background

        Returns:
            Name of the created index
        """
        try:
            collection = self.get_collection(collection_name)
            index_name = collection.create_index(
                keys, unique=unique, background=background
            )
            logger.info(
                f"Created index '{index_name}' on collection '{collection_name}'"
            )
            return index_name
        except Exception as e:
            logger.error(f"Error creating index: {e}")
            raise

    def drop_collection(self, collection_name: str) -> None:
        """
        Drop a collection from the database.

        Args:
            collection_name: Name of the collection to drop
        """
        try:
            self.database.drop_collection(collection_name)
            logger.info(f"Dropped collection: {collection_name}")
        except Exception as e:
            logger.error(f"Error dropping collection: {e}")
            raise

    def list_collections(self) -> List[str]:
        """
        List all collections in the database.

        Returns:
            List of collection names
        """
        try:
            return self.database.list_collection_names()
        except Exception as e:
            logger.error(f"Error listing collections: {e}")
            raise

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


# Global client instance for simple usage
_global_client: Optional[MongoDBClient] = None


def get_client() -> MongoDBClient:
    """
    Get a global MongoDB client instance.

    This is useful for simple applications that only need one connection.
    For more complex applications, consider creating multiple client instances.

    Returns:
        Global MongoDB client instance
    """
    global _global_client
    if _global_client is None:
        _global_client = MongoDBClient()
    return _global_client


def close_client() -> None:
    """Close the global MongoDB client."""
    global _global_client
    if _global_client:
        _global_client.disconnect()
        _global_client = None
