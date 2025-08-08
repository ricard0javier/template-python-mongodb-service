#!/bin/bash

# MongoDB Cluster Validation Script
# This script checks the health and configuration of the MongoDB replica set


# example of how to run the script
# ./scripts/validate-cluster-healthcheck.sh
# or
# MONGO_HOST1=mongodb1 MONGO_PORT1=27017 MONGO_HOST2=mongodb2 MONGO_PORT2=27018 MONGO_HOST3=mongodb3 MONGO_PORT3=27019 ./scripts/validate-cluster-healthcheck.sh
# or for localhost:
# MONGO_HOST1=mongodb1 MONGO_PORT1=27017 MONGO_HOST2=mongodb2 MONGO_PORT2=27018 MONGO_HOST3=mongodb3 MONGO_PORT3=27019 ./scripts/validate-cluster-healthcheck.sh


# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values for MongoDB connection
MONGO_AUTH_DB=${MONGO_AUTH_DB:-"admin"}
MONGO_HOST1=${MONGO_HOST1:-"mongodb1"}
MONGO_HOST2=${MONGO_HOST2:-"mongodb2"}
MONGO_HOST3=${MONGO_HOST3:-"mongodb3"}
MONGO_PORT1=${MONGO_PORT1:-"27017"}
MONGO_PORT2=${MONGO_PORT2:-"27018"}
MONGO_PORT3=${MONGO_PORT3:-"27019"}

echo -e "${YELLOW}Starting MongoDB cluster validation...${NC}"

# Function to check if a MongoDB instance is running
check_mongodb_instance() {
    local host=$1
    local port=$2
    local instance_name=$3
    
    if mongosh "mongodb://${host}:${port}/${MONGO_AUTH_DB}" --eval "db.serverStatus()" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ MongoDB instance $instance_name ($host) is running${NC}"
        return 0
    else
        echo -e "${RED}✗ MongoDB instance $instance_name ($host) is not running${NC}"
        return 1
    fi
}

# Function to check replica set status
check_replica_set() {
    local primary_host=$1
    
    echo -e "${YELLOW}Checking replica set status...${NC}"
    
    # Get replica set status
    local rs_status=$(mongosh "mongodb://${primary_host}:${MONGO_PORT}/${MONGO_AUTH_DB}" --eval "rs.status()" 2>/dev/null)
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}✗ Failed to get replica set status${NC}"
        return 1
    fi
    
    # Check if replica set is properly configured
    local set_name=$(echo "$rs_status" | grep -o "set: '[^']*'" | cut -d"'" -f2)
    if [ "$set_name" != "rs0" ]; then
        echo -e "${RED}✗ Replica set name is not 'rs0'${NC}"
        return 1
    fi
    
    # Count members
    local member_count=$(echo "$rs_status" | grep -c "name: '[^']*'")
    if [ "$member_count" -ne 3 ]; then
        echo -e "${RED}✗ Expected 3 members in replica set, found $member_count${NC}"
        return 1
    fi
    
    # Check member states
    local healthy_members=$(echo "$rs_status" | grep -c "stateStr: 'PRIMARY'\|stateStr: 'SECONDARY'")
    if [ "$healthy_members" -ne 3 ]; then
        echo -e "${RED}✗ Not all members are in PRIMARY or SECONDARY state${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✓ Replica set is properly configured with 3 members${NC}"
    return 0
}

# Check each MongoDB instance
check_mongodb_instance $MONGO_HOST1 $MONGO_PORT1 "mongodb1" || exit 1
check_mongodb_instance $MONGO_HOST2 $MONGO_PORT2 "mongodb2" || exit 1
check_mongodb_instance $MONGO_HOST3 $MONGO_PORT3 "mongodb3" || exit 1

# Check replica set status
check_replica_set $MONGO_HOST1 $MONGO_PORT1 || exit 1

echo -e "${GREEN}✓ MongoDB cluster validation completed successfully${NC}"
exit 0 
