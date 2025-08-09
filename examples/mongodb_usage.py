#!/usr/bin/env python3
"""
Example usage of the MongoDB client.

This file demonstrates how to use the MongoDB client with various operations.
Run this after setting up your MongoDB connection string in the environment.
"""

import sys
import os
from datetime import datetime

# Add the src directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from persistence.mongodb import MongoDBClient, get_client
from bson import ObjectId


def example_basic_operations():
    """Demonstrate basic CRUD operations."""
    print("=== Basic Operations Example ===")

    # Option 1: Use the global client (simple approach)
    client = get_client()

    # Option 2: Create your own client instance (recommended for complex apps)
    # client = MongoDBClient()
    # client.connect()

    try:
        # Health check
        if client.health_check():
            print("✓ MongoDB connection is healthy")
        else:
            print("✗ MongoDB connection failed")
            return

        collection_name = "example_users"

        # Insert a single document
        user_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30,
            "created_at": datetime.utcnow(),
            "preferences": {"theme": "dark", "notifications": True},
        }

        user_id = client.insert_one(collection_name, user_data)
        print(f"✓ Inserted user with ID: {user_id}")

        # Insert multiple documents
        users_data = [
            {
                "name": "Jane Smith",
                "email": "jane@example.com",
                "age": 25,
                "created_at": datetime.utcnow(),
            },
            {
                "name": "Bob Johnson",
                "email": "bob@example.com",
                "age": 35,
                "created_at": datetime.utcnow(),
            },
        ]

        user_ids = client.insert_many(collection_name, users_data)
        print(f"✓ Inserted {len(user_ids)} users")

        # Find a single document
        found_user = client.find_one(collection_name, {"email": "john@example.com"})
        if found_user:
            print(f"✓ Found user: {found_user['name']}")

        # Find multiple documents with filtering and sorting
        young_users = client.find_many(
            collection_name,
            {"age": {"$lt": 30}},  # Users younger than 30
            projection={"name": 1, "age": 1, "_id": 0},  # Only return name and age
            sort=[("age", 1)],  # Sort by age ascending
        )
        print(
            f"✓ Found {len(young_users)} young users: {[u['name'] for u in young_users]}"
        )

        # Update a document
        modified_count = client.update_one(
            collection_name,
            {"email": "john@example.com"},
            {"$set": {"age": 31, "last_updated": datetime.utcnow()}},
        )
        print(f"✓ Updated {modified_count} user(s)")

        # Count documents
        total_users = client.count_documents(collection_name)
        print(f"✓ Total users in collection: {total_users}")

        # Aggregation example
        age_stats = client.aggregate(
            collection_name,
            [
                {
                    "$group": {
                        "_id": None,
                        "avg_age": {"$avg": "$age"},
                        "min_age": {"$min": "$age"},
                        "max_age": {"$max": "$age"},
                        "total_users": {"$sum": 1},
                    }
                }
            ],
        )

        if age_stats:
            stats = age_stats[0]
            print(
                f"✓ Age statistics: avg={stats['avg_age']:.1f}, min={stats['min_age']}, max={stats['max_age']}"
            )

        # Clean up - delete the test documents
        deleted_count = client.delete_many(collection_name, {})
        print(f"✓ Cleaned up {deleted_count} test documents")

    except Exception as e:
        print(f"✗ Error during operations: {e}")


def example_with_context_manager():
    """Demonstrate using the client as a context manager."""
    print("\n=== Context Manager Example ===")

    # Using context manager ensures proper cleanup
    with MongoDBClient() as client:
        if not client.health_check():
            print("✗ MongoDB connection failed")
            return

        collection_name = "example_products"

        # Sample product data
        products = [
            {
                "name": "Laptop",
                "category": "Electronics",
                "price": 999.99,
                "in_stock": True,
            },
            {
                "name": "Desk Chair",
                "category": "Furniture",
                "price": 199.99,
                "in_stock": True,
            },
            {
                "name": "Coffee Mug",
                "category": "Kitchen",
                "price": 15.99,
                "in_stock": False,
            },
        ]

        try:
            # Insert products
            product_ids = client.insert_many(collection_name, products)
            print(f"✓ Inserted {len(product_ids)} products")

            # Find products in stock
            in_stock_products = client.find_many(
                collection_name,
                {"in_stock": True},
                sort=[("price", -1)],  # Sort by price descending
            )
            print(f"✓ Found {len(in_stock_products)} products in stock")

            # Update product stock
            client.update_one(
                collection_name,
                {"name": "Coffee Mug"},
                {"$set": {"in_stock": True, "stock_count": 50}},
            )
            print("✓ Updated Coffee Mug stock status")

            # Create an index for better query performance
            index_name = client.create_index(
                collection_name, [("category", 1), ("price", -1)]
            )
            print(f"✓ Created index: {index_name}")

            # List all collections
            collections = client.list_collections()
            print(f"✓ Database collections: {collections}")

            # Clean up
            client.drop_collection(collection_name)
            print(f"✓ Dropped collection: {collection_name}")

        except Exception as e:
            print(f"✗ Error during context manager operations: {e}")


def example_transactions():
    """Demonstrate transaction usage."""
    print("\n=== Transaction Example ===")

    client = get_client()

    try:
        if not client.health_check():
            print("✗ MongoDB connection failed")
            return

        # Example: Transfer money between accounts
        accounts_collection = "example_accounts"

        # Setup test accounts
        accounts = [
            {"account_id": "acc_001", "name": "Alice", "balance": 1000.00},
            {"account_id": "acc_002", "name": "Bob", "balance": 500.00},
        ]

        client.insert_many(accounts_collection, accounts)
        print("✓ Created test accounts")

        # Transfer $200 from Alice to Bob
        transfer_amount = 200.00

        with client.transaction():
            # Debit from Alice's account
            alice_result = client.update_one(
                accounts_collection,
                {"account_id": "acc_001", "balance": {"$gte": transfer_amount}},
                {"$inc": {"balance": -transfer_amount}},
            )

            if alice_result == 0:
                raise Exception("Insufficient funds in Alice's account")

            # Credit to Bob's account
            client.update_one(
                accounts_collection,
                {"account_id": "acc_002"},
                {"$inc": {"balance": transfer_amount}},
            )

            print(f"✓ Successfully transferred ${transfer_amount} from Alice to Bob")

        # Verify final balances
        alice_balance = client.find_one(accounts_collection, {"account_id": "acc_001"})[
            "balance"
        ]
        bob_balance = client.find_one(accounts_collection, {"account_id": "acc_002"})[
            "balance"
        ]

        print(f"✓ Final balances - Alice: ${alice_balance}, Bob: ${bob_balance}")

        # Clean up
        client.delete_many(accounts_collection, {})
        print("✓ Cleaned up test accounts")

    except Exception as e:
        print(f"✗ Transaction failed: {e}")


def example_error_handling():
    """Demonstrate error handling."""
    print("\n=== Error Handling Example ===")

    client = get_client()

    try:
        collection_name = "example_unique_test"

        # Create a unique index
        client.create_index(collection_name, "email", unique=True)
        print("✓ Created unique index on email field")

        # Insert first document
        client.insert_one(
            collection_name, {"email": "test@example.com", "name": "Test User"}
        )
        print("✓ Inserted first document")

        # Try to insert duplicate - this should be handled gracefully
        duplicate_id = client.insert_one(
            collection_name, {"email": "test@example.com", "name": "Duplicate User"}
        )

        if duplicate_id is None:
            print("✓ Duplicate insertion was properly handled (returned None)")
        else:
            print("✗ Duplicate insertion should have been rejected")

        # Clean up
        client.drop_collection(collection_name)
        print(f"✓ Cleaned up test collection")

    except Exception as e:
        print(f"✗ Error handling example failed: {e}")


if __name__ == "__main__":
    print("MongoDB Client Usage Examples")
    print("=" * 40)

    try:
        example_basic_operations()
        example_with_context_manager()
        example_transactions()
        example_error_handling()

        print("\n" + "=" * 40)
        print("✓ All examples completed successfully!")

    except Exception as e:
        print(f"\n✗ Examples failed with error: {e}")

    finally:
        # Clean up global client
        from persistence.mongodb import close_client

        close_client()
        print("✓ Closed MongoDB connections")
