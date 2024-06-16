#!/bin/bash
# Usage: ./start.sh <service_name> <service_name> ...
# Description: This script is used to start the services in the docker-compose.yml file

# Get this file directory
DIR=$(dirname "${BASH_SOURCE[0]}")

echo "Starting services... ${@}"

# Check for .env file
if [ ! -f "${DIR}/.env" ]; then
    echo "Creating .env file"
    cp "${DIR}/.env.example" "${DIR}/.env"
fi

# Implement the docker-compose.yml file
#cp "${DIR}/orchestrator-init "${DIR}/wasmiot-orchestrator/init"

docker compose -f "${DIR}/docker-compose.yml" --profile device up --pull always ${@}
