#!/bin/bash

# Exit on error
set -e

# Configuration
# Source: https://huggingface.co/datasets/MongoDB/embedded_movies
SAMPLE_DATA_URL="https://huggingface.co/datasets/MongoDB/embedded_movies/resolve/main/sample_mflix.embedded_movies.json?download=true"
SAMPLE_DATA_FILE="sample_movies.json"
DB_NAME="sample_mflix"
COLLECTION_NAME="embedded_movies"
CONNECTION_STRING="mongodb://mongodb1:27017,mongodb2:27018,mongodb3:27019/?replicaSet=rs0"


echo "Downloading sample movies data..."
curl -L -o "$SAMPLE_DATA_FILE" "$SAMPLE_DATA_URL"

echo "Loading data into local MongoDB cluster..."
mongoimport --uri "$CONNECTION_STRING" \
    --db "$DB_NAME" \
    --collection "$COLLECTION_NAME" \
    --file "$SAMPLE_DATA_FILE" \
    --jsonArray

echo "Data loaded successfully into local cluster!"

# Clean up
rm "$SAMPLE_DATA_FILE"

echo "Done!"