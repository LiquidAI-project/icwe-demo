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

## Citation

To cite this work, please use the following BibTeX entry:

```bibtex
@InProceedings{10.1007/978-3-031-62362-2_28,
    author="Kotilainen, Pyry
        and J{\"a}rvinen, Viljami
        and Autto, Teemu
        and Rathnayaka, Lakshan
        and Mikkonen, Tommi",
    editor="Stefanidis, Kostas
        and Syst{\"a}, Kari
        and Matera, Maristella
        and Heil, Sebastian
        and Kondylakis, Haridimos
        and Quintarelli, Elisa",
    title="Demonstrating Liquid Software in IoT Using WebAssembly",
    booktitle="Web Engineering",
    year="2024",
    publisher="Springer Nature Switzerland",
    address="Cham",
    pages="381--384",
    abstract="In this paper we introduce a demonstration of our prototype orchestration system utilising WebAssembly to achieve isomorphism for a liquid software IoT system. The demonstration hardware consists of two Raspberry Pi IoT devices and a computer acting as the orchestrator. The audience can interact with the orchestrator through a web interface to deploy different software configurations to the devices, and observe the deployment process as well as the deployed application in action.",
    isbn="978-3-031-62362-2"
}
```
