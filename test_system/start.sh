#!/bin/bash
# Get this file directory
DIR=$(dirname "${BASH_SOURCE[0]}")

# Check for .env file
if [ ! -f "${DIR}/.env" ]; then
    echo "Creating .env file"
    cp "${DIR}/.env.example" "${DIR}/.env"
fi

# Implement the docker-compose.yml file
#cp "${DIR}/orchestrator-init "${DIR}/wasmiot-orchestrator/init"

docker compose -f "${DIR}/docker-compose.yml" --profile device up --build --pull always
