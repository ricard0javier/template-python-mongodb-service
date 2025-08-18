import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# MongoDB Configuration
MONGODB_URI = os.getenv(
    "MONGODB_URI",
    "mongodb://admin:admin@localhost:27027/?directConnection=true",
)

MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "whatsup")

# Connection settings
MONGODB_MAX_POOL_SIZE = int(os.getenv("MONGODB_MAX_POOL_SIZE", "100"))
MONGODB_MIN_POOL_SIZE = int(os.getenv("MONGODB_MIN_POOL_SIZE", "10"))
MONGODB_MAX_IDLE_TIME_MS = int(os.getenv("MONGODB_MAX_IDLE_TIME_MS", "30000"))
MONGODB_CONNECT_TIMEOUT_MS = int(os.getenv("MONGODB_CONNECT_TIMEOUT_MS", "10000"))
MONGODB_SERVER_SELECTION_TIMEOUT_MS = int(
    os.getenv("MONGODB_SERVER_SELECTION_TIMEOUT_MS", "5000")
)
MONGODB_COLLECTION_EVENT_STORE = os.getenv(
    "MONGODB_COLLECTION_EVENT_STORE", "event_store"
)

# Retry configuration
MONGODB_RETRY_WRITES = os.getenv("MONGODB_RETRY_WRITES", "true").lower() == "true"
MONGODB_RETRY_READS = os.getenv("MONGODB_RETRY_READS", "true").lower() == "true"

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "openai:gpt-5-chat-latest")

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092")
KAFKA_AUTO_OFFSET_RESET = os.getenv("KAFKA_AUTO_OFFSET_RESET", "earliest")
KAFKA_BLOCKING_RUN = os.getenv("KAFKA_BLOCKING_RUN", "true").lower() == "true"
KAFKA_CONSUMER_GROUP = os.getenv(
    "KAFKA_CONSUMER_GROUP", "whatsup-message-received-group"
)
KAFKA_CONSUMER_MESSAGE = os.getenv("KAFKA_CONSUMER_MESSAGE", "whatsup.message.received")
KAFKA_CONSUMER_DLQ_TOPIC = os.getenv(
    "KAFKA_CONSUMER_DLQ_TOPIC", "whatsup.message.received-dlq"
)

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
