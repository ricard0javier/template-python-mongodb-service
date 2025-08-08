import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve MongoDB URI
MONGODB_URI = os.getenv(
    "MONGODB_URI",
    "mongodb://mongodb1:27017,mongodb2:27018,mongodb3:27019/?replicaSet=rs0",
)
