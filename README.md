# icwe-demo
WasmIoT demonstration for ICWE 2024 conference

## Running UI

Create a python virtual environment and install the requirements:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

Run the UI:
```bash
# Optional: set the environment variable to the URL of the WasmIoT server
export WASMIOT_ORCHESTRATOR_URL=http://orchestrator.local:5000
python -m icwe-demo
```
