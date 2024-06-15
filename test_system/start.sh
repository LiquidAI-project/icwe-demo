cp orchestrator-init wasmiot-orchestrator/init
docker compose --env-file .env -f docker-compose.example-system.yml --profile device up --build
