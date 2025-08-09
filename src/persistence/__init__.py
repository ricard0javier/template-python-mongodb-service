"""
Persistence layer for the application.

This module provides database connectivity and data access patterns.
"""

from .mongodb import MongoDBClient, get_client, close_client

__all__ = ["MongoDBClient", "get_client", "close_client"]
