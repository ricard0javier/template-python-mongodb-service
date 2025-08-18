# AI Agent with MongoDB

An agent implementation to create replies to messages received, using RAG extracting previous messages from MongoDB and using MongoDB as an Event Store

Get started by running `make install dev` to create an instance of MongoDB Atlas CLI, setup the Redpanda topics and start a Redpanda Console.

The connection string for MongoDB is:
`mongodb://admin:admin@localhost:27027/?directConnection=true`

The URL to access Redpanda console is:
`http://localhost:8080/`

## Features

- Integration with MongoDB
- Docker Compose setup for local development
- Integration with Kafka

## Prerequisites

- Python 3.13.\*
- [Conda](https://www.anaconda.com/docs/getting-started/miniconda/install)
- Docker and Docker Compose
- Make (optional, for using Makefile commands)
- Snappy Compression Library - `brew install snappy`: To support compressed messages sent from Redpanda Console

## Getting Started

### Environment Variables

#### MongoDB Configuration

- `MONGODB_URI` - MongoDB connection string (default: `mongodb://admin:admin@localhost:27027/?directConnection=true`)
- `MONGODB_DATABASE` - Database name (default: `whatsup`)
- `MONGODB_MAX_POOL_SIZE` - Maximum connection pool size (default: `100`)
- `MONGODB_MIN_POOL_SIZE` - Minimum connection pool size (default: `10`)
- `MONGODB_MAX_IDLE_TIME_MS` - Maximum idle time for connections in ms (default: `30000`)
- `MONGODB_CONNECT_TIMEOUT_MS` - Connection timeout in ms (default: `10000`)
- `MONGODB_SERVER_SELECTION_TIMEOUT_MS` - Server selection timeout in ms (default: `5000`)
- `MONGODB_RETRY_WRITES` - Enable retry writes (default: `true`)
- `MONGODB_RETRY_READS` - Enable retry reads (default: `true`)

#### OpenAI Configuration

- `OPENAI_API_KEY` - Your OpenAI API key (required)
- `OPENAI_MODEL_NAME` - OpenAI model to use (default: `openai:gpt-5-chat-latest`)

#### Kafka Configuration

- `KAFKA_BOOTSTRAP_SERVERS` - Kafka bootstrap servers (default: `localhost:19092`)
- `KAFKA_AUTO_OFFSET_RESET` - Kafka offset reset policy (default: `earliest`)
- `KAFKA_BLOCKING_RUN` - Enable blocking run mode (default: `true`)
- `KAFKA_CONSUMER_GROUP` - Consumer group ID (default: `whatsup-message-received-group`)
- `KAFKA_CONSUMER_MESSAGE` - Topic to consume messages from (default: `whatsup.message.received`)
- `KAFKA_CONSUMER_DLQ_TOPIC` - Dead letter queue topic (default: `whatsup.message.received-dlq`)

#### Event Store Configuration

- `MONGODB_COLLECTION_EVENT_STORE` - Collection name for event store (default: `event_store`)

#### Logging

- `LOG_LEVEL` - Logging level (default: `INFO`)

### Local Development

1. Clean and Install dependencies:

   ```bash
   make clean install
   ```

2. Start the development server:
   ```bash
   make dev
   ```

## Development Commands

- `make clean`: Clean build artifacts
- `make install`: Install dependencies
- `make dev`: Start development server, including MongoDB, Redpanda and Redpanda Console with basic setup

## Kafka

### Consumer

This service receives integration events on the topic defined by the environment variable `KAFKA_CONSUMER_MESSAGE`
(default: `whatsup.message.received`) and the message schema is as follow:

```json
{
  "_id": "68a311911b1dbaa23ae9adf1", //event id
  "eventType": "whatsup.message.received", // event type
  "metadata": {
    "schema_version": "1", // schema version
    "source": "whatsup-service",
    "traceId": "7230ce81-86e5-46e0-a790-c1b476280c72", // end-to-end trace
    "correlationId": "0693dbeb-e7b2-47ef-a5f6-125939283563", // original message id
    "causationId": "04089f64-0fc6-4c78-8310-58862cd38228", // event We Reacted To
    "occurredAt": "2025-08-18T12:34:56Z" // when it was created
  },
  "aggregate": {
    // domain identifier
    "type": "Conversation", // domain name
    "id": "447700900123@c.us", //entity id
    "subType": "MessageReceived", // sub category of the aggregate
    "sequenceNr": "1" // incremental unique for this aggregate type and sub type
  },
  "payload": {
    // extra information
    "chatId": "447700900123@c.us", // unique identifier of the conversation
    "from": "+447700...", // identifier of the sender
    "to": "+447911...", // identifier of the receiver
    "text": "Can we talk at 5?", // text of the message
    "isFromSelf": false // true if the message is sent by subscriber
  }
}
```

#### Indepontency Check

It verifies that this service hasn't created a reply for this event before. avoiding extra costs and processing

```json
{
  "metadata": {
    "source": "whatsup-assistant",
    "causationId": "68a311911b1dbaa23ae9adf1" // incoming event._id
  }
}
```

#### Processing

If the message comes from the subscriber, it will be stored in the database for future RAG operations.  
Previous messages from the conversation will be retrieved to feed the LLM and generate the assistant response.  
When a message is produced by the assistant it will be pushed as explained in "Events Produced".  
If there is an error, the message will be sent to the DLQ Topic, called as the consumer topic and suffixed wit `-dlq`.
The value of the message will be the same but extra information will be added to the headers:

```json
{
  "metadata": {
    "schema_version": "1", // schema version
    "source": "whatsup-assistant",
    "traceId": "7230ce81-86e5-46e0-a790-c1b476280c72", // end-to-end trace
    "correlationId": "0693dbeb-e7b2-47ef-a5f6-125939283563", // original message id
    "causationId": "68a311911b1dbaa23ae9adf1", // event We Reacted To
    "occurredAt": "2025-08-18T12:34:57Z", // when it was created
    "errorType": "System Error",
    "error": "LLM cannot be reached... or whatever error"
  }
}
```

### Events Produced

On successful processing, a new event will be stored in the collection named using the environment variable `MONGODB_COLLECTION_EVENT_STORE`
(default: `event_store`), and the message will look like this:

```json
{
  "_id": "68a311911b1dbaa23ae9adf4", //event id
  "eventType": "whatsup.message.generated", // event type
  "metadata": {
    "schema_version": "1", // schema version
    "source": "whatsup-assistant",
    "traceId": "7230ce81-86e5-46e0-a790-c1b476280c72", // end-to-end trace
    "correlationId": "0693dbeb-e7b2-47ef-a5f6-125939283563", // original message id
    "causationId": "68a311911b1dbaa23ae9adf1", // event We Reacted To
    "occurredAt": "2025-08-18T12:34:57Z" // when it was created
  },
  "aggregate": {
    // domain identifier
    "type": "Conversation", // domain name
    "id": "447700900123@c.us", //entity id
    "subType": "MessageGenerated", // sub category of the aggregate
    "sequenceNr": "2" // incremental unique for this aggregate type and sub type
  },
  "payload": {
    // extra information
    "chatId": "447700900123@c.us", // unique identifier of the conversation
    "from": "+447911...", // identifier of the receiver
    "to": "+447700...", // identifier of the sender
    "text": "I'm busy today, but I'll call you later", // text of the message
    "isFromSelf": true // true if the message is sent by subscriber
  }
}
```

If the message doesn't require a response, the event generated is similar to the previous but the following keys will be different:

```json
{
  "aggregate": {
    "subType": "MessageIgnored"
  }
}
```

These events are later consumed by another service using MongoDB's Change Stream and publishing to Kafka, to avoid dual-write bugs.

## Sample Events

This service consumes events from the Kafka topic configured in `KAFKA_CONSUMER_MESSAGE` (default: `whatsup.message.received`). Below are sample events that can be sent to test the service:

### Basic Message Event
