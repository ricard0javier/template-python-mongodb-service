import json
import logging
import signal
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import NoBrokersAvailable

from ..config import (
    KAFKA_AUTO_OFFSET_RESET,
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_CONSUMER_DLQ_TOPIC,
    KAFKA_CONSUMER_GROUP,
    KAFKA_CONSUMER_MESSAGE,
    MONGODB_COLLECTION_EVENT_STORE,
)
from ..examples.agent_with_mongodb_memory import invoke_agent
from ..persistence.mongodb import get_client

logger = logging.getLogger(__name__)


def _is_processed(event_id: str) -> bool:
    """Check if event has already been processed using the event store."""
    client = get_client()
    collection = client.get_collection(MONGODB_COLLECTION_EVENT_STORE)

    # Check if we already have a response event for this causationId
    return (
        collection.find_one(
            {"metadata.causationId": event_id, "metadata.source": "whatsup-assistant"}
        )
        is not None
    )


def _generate_response(event: Dict[str, Any]) -> str:
    """Generate response using agent with conversation context."""
    chat_id = event["aggregate"]["id"]
    user_message = event["payload"]["text"]

    # Invoke agent - it already has access to conversation history through memory
    result = invoke_agent(
        thread_id=chat_id,
        sender_type="contact",
        sender_name="User",
        receiver_name="Assistant",
        user_message=user_message,
    )

    # Log the result type for debugging
    response = result["messages"][-1].content
    logger.debug("Agent response: %s", response)
    return response


def _create_response_event(
    original_event: Dict[str, Any],
    response_text: str,
    sub_type: str = "MessageGenerated",
) -> Dict[str, Any]:
    """Create response event following the schema from README."""
    now = datetime.now(timezone.utc).isoformat()

    return {
        "_id": str(uuid.uuid4()),
        "eventType": "whatsup.message.generated",
        "metadata": {
            "schema_version": "1",
            "source": "whatsup-assistant",
            "traceId": original_event["metadata"]["traceId"],
            "correlationId": original_event["metadata"]["correlationId"],
            "causationId": original_event["_id"],
            "occurredAt": now,
        },
        "aggregate": {
            "type": original_event["aggregate"]["type"],
            "id": original_event["aggregate"]["id"],
            "subType": sub_type,
            "sequenceNr": str(int(original_event["aggregate"]["sequenceNr"]) + 1),
        },
        "payload": {
            "chatId": original_event["payload"]["chatId"],
            "from": original_event["payload"]["to"],  # Swap sender/receiver
            "to": original_event["payload"]["from"],
            "text": response_text,
            "isFromSelf": True,
        },
    }


def _store_event_in_event_store(event: Dict[str, Any]) -> None:
    """Store event in the event store collection."""
    # Ensure the event is MongoDB-serializable
    safe_event = _make_mongodb_safe(event)

    client = get_client()
    collection = client.get_collection(MONGODB_COLLECTION_EVENT_STORE)
    collection.insert_one(safe_event)


def _make_mongodb_safe(obj: Any) -> Any:
    """Recursively convert objects to MongoDB-safe types."""
    if isinstance(obj, dict):
        return {k: _make_mongodb_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_make_mongodb_safe(item) for item in obj]
    elif hasattr(obj, "__dict__"):
        # Convert objects to string representation
        return str(obj)
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    else:
        # Convert any other types to string
        return str(obj)


def _store_message_for_rag(event: Dict[str, Any]) -> None:
    """Store incoming message in database for future RAG operations."""
    client = get_client()
    collection = client.get_collection("messages")

    message_doc = {
        "chatId": event["aggregate"]["id"],
        "from": event["payload"]["from"],
        "to": event["payload"]["to"],
        "text": event["payload"]["text"],
        "isFromSelf": event["payload"]["isFromSelf"],
        "timestamp": event["metadata"]["occurredAt"],
        "event_id": event["_id"],
        "eventType": event["eventType"],
    }

    collection.insert_one(message_doc)
    logger.debug("Stored message for RAG: %s", event["_id"])


def _process_message(event: Dict[str, Any]) -> None:
    """Process incoming message event."""
    # Store ALL incoming messages for RAG operations
    _store_message_for_rag(event)

    # Only generate response for messages from subscribers (not from self)
    if not event["payload"]["isFromSelf"]:
        try:
            response_text = _generate_response(event)
            response_event = _create_response_event(event, response_text)
            _store_event_in_event_store(response_event)
            logger.info("Generated response for chat %s", event["aggregate"]["id"])
        except Exception as e:
            logger.error("Failed to generate response: %s", str(e))
            raise
    else:
        logger.info(
            "Message from self, no response needed for chat %s",
            event["aggregate"]["id"],
        )


def _send_to_dlq(
    event: Dict[str, Any], error_type: str, error_message: str
) -> Dict[str, Any]:
    """Send failed event to Dead Letter Queue."""
    dlq_event = event.copy()

    # Ensure metadata exists
    if "metadata" not in dlq_event:
        dlq_event["metadata"] = {}

    dlq_event["metadata"]["errorType"] = error_type
    dlq_event["metadata"]["error"] = error_message
    dlq_event["metadata"]["occurredAt"] = datetime.now(timezone.utc).isoformat()

    return dlq_event


def run_kafka_consumer(stop_event: threading.Event) -> None:
    """Run the Kafka consumer main loop."""
    consumer = None
    producer = None
    backoff_seconds = 2

    # Initialize Kafka connections
    while not stop_event.is_set() and (consumer is None or producer is None):
        try:
            consumer = KafkaConsumer(
                KAFKA_CONSUMER_MESSAGE,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                group_id=KAFKA_CONSUMER_GROUP,
                enable_auto_commit=False,
                auto_offset_reset=KAFKA_AUTO_OFFSET_RESET,
                value_deserializer=lambda v: v.decode("utf-8"),
                key_deserializer=lambda v: v.decode("utf-8") if v else None,
                max_poll_records=50,
                session_timeout_ms=10000,
                request_timeout_ms=30000,
            )
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                key_serializer=lambda v: v.encode("utf-8") if isinstance(v, str) else v,
                value_serializer=lambda v: json.dumps(v).encode("utf-8")
                if not isinstance(v, (bytes, bytearray))
                else v,
                acks="all",
                linger_ms=10,
                retries=5,
                max_in_flight_requests_per_connection=1,
            )
        except NoBrokersAvailable:
            logger.warning(
                "Kafka brokers not available at %s. Retrying in %ss...",
                KAFKA_BOOTSTRAP_SERVERS,
                backoff_seconds,
            )
            time.sleep(backoff_seconds)
            backoff_seconds = min(backoff_seconds * 2, 30)
            continue
        except Exception:
            logger.exception("Error creating Kafka consumer/producer. Retrying...")
            time.sleep(backoff_seconds)
            backoff_seconds = min(backoff_seconds * 2, 30)
            continue

    logger.info(
        "Kafka consumer started for topic '%s' on %s, group_id=%s",
        KAFKA_CONSUMER_MESSAGE,
        KAFKA_BOOTSTRAP_SERVERS,
        KAFKA_CONSUMER_GROUP,
    )

    try:
        while not stop_event.is_set():
            records = consumer.poll(timeout_ms=1000)
            if not records:
                continue

            for _topic_partition, message_list in records.items():
                if not message_list:
                    continue

                for msg in message_list:
                    try:
                        # Parse event
                        event = json.loads(msg.value)
                        event_id = event.get("_id")

                        if not event_id:
                            logger.warning("Skipping message without event ID")
                            consumer.commit()
                            continue

                        # Check idempotency
                        if _is_processed(event_id):
                            logger.warning(
                                "Skipping already-processed event %s", event_id
                            )
                            consumer.commit()
                            continue

                        # Process message
                        _process_message(event)

                        # Commit offset
                        consumer.commit()

                    except json.JSONDecodeError:
                        logger.warning("Skipping non-JSON message")
                        consumer.commit()
                        continue
                    except Exception as e:
                        logger.exception("Failed processing event: %s", str(e))

                        # Send to DLQ
                        try:
                            # Create a safe event object for DLQ
                            safe_event = (
                                event if "event" in locals() else {"_id": "unknown"}
                            )
                            safe_event_id = (
                                event_id if "event_id" in locals() else "unknown"
                            )

                            dlq_event = _send_to_dlq(
                                safe_event,
                                "System Error",
                                str(e),
                            )

                            producer.send(
                                KAFKA_CONSUMER_DLQ_TOPIC,
                                key=safe_event_id,
                                value=dlq_event,
                            )
                            producer.flush(timeout=5)
                        except Exception:
                            logger.exception("Failed sending to DLQ")

                        # Commit to move on
                        consumer.commit()
                        time.sleep(1)

    finally:
        try:
            if consumer is not None:
                consumer.close()
        except Exception:
            logger.exception("Error closing Kafka consumer")
        try:
            if producer is not None:
                producer.flush(timeout=2)
                producer.close()
        except Exception:
            logger.exception("Error closing Kafka producer")


def start_consumer() -> None:
    """Start the Kafka consumer with graceful shutdown."""
    stop_event = threading.Event()

    def _handle_signal(signum):
        logger.info("Received signal %s, stopping Kafka consumer...", signum)
        stop_event.set()

    try:
        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)
    except Exception:
        # Not all contexts allow setting signals (e.g., certain test runners)
        pass

    run_kafka_consumer(stop_event)
