#!/bin/bash

# Script to add/update MongoDB host entries in the hosts file
# Requires sudo privileges

# MongoDB hosts configuration
MONGODB_HOSTS=(
    "127.0.0.1 mongodb1"
    "127.0.0.1 mongodb2"
    "127.0.0.1 mongodb3"
)

# Function to check if running on macOS
is_macos() {
    [[ "$(uname)" == "Darwin" ]]
}

# Function to get the hosts file path
get_hosts_file() {
    if is_macos; then
        echo "/private/etc/hosts"
    else
        echo "/etc/hosts"
    fi
}

# Function to check if a host entry exists
host_entry_exists() {
    local hostname=$1
    local hosts_file=$(get_hosts_file)
    grep -q "$hostname" "$hosts_file"
}

# Function to add or update host entries
update_hosts() {
    local hosts_file=$(get_hosts_file)
    local temp_file=$(mktemp)

    # Create backup of hosts file
    echo "Creating backup of hosts file..."
    sudo cp "$hosts_file" "${hosts_file}.bak"

    # Process each MongoDB host entry
    for entry in "${MONGODB_HOSTS[@]}"; do
        local hostname=$(echo "$entry" | awk '{print $2}')
        
        if host_entry_exists "$hostname"; then
            # Update existing entry
            echo "Updating entry for $hostname..."
            sudo sed -i.bak "/$hostname/d" "$hosts_file"
        else
            echo "Adding new entry for $hostname..."
        fi
        
        # Add the new entry
        echo "$entry" | sudo tee -a "$hosts_file" > /dev/null
    done

    echo "Hosts file updated successfully!"
    echo "A backup of the original hosts file has been created at ${hosts_file}.bak"
}

# Main execution
if [ "$(id -u)" != "0" ]; then
    echo "This script must be run as root or with sudo privileges"
    exit 1
fi

update_hosts 