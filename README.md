# icwe-demo
WasmIoT demonstration for ICWE 2024 conference

## Running the test setup in docker

For convenience there is a `test_system/docker-compose.yml` and `test_system/start.sh` scripts. The `start.sh` script will start the WasmIoT orchestrator ([`orchestrator`](http://localhost:3000)), the ICWE2024 demo ([`icwe-demo`](http://localhost:7860)) and two wasmiot supervisors ([`raspi1`](http://localhost:3001)) and [`raspi2`](http://localhost:3002)).

To start all or any service, run the following command:
```sh
./test_system/start.sh [service]
```

When starting from devcontainer, the default app is `icwe-demo`. To start the necessary services, run the following command:
```sh
./test_system/start.sh orchestrator raspi1 raspi2
```

## Running UI locally

Create a python virtual environment and install the requirements:
```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

Run the UI:
```sh
# Optional: set the environment variable to the URL of the WasmIoT server
export WASMIOT_ORCHESTRATOR_URL=http://orchestrator.local:5000
python -m icwe-demo
```
