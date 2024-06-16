"""
UI for WasmIoT demo.
====================

Important environment variables:
- :env:`os.environ['WASMIOT_ORCHESTRATOR_URL']` - URL of orchestrator

To define workflows, see :var:`MANIFESTS`.

"""

import collections
import datetime
import logging
import threading
import time
from typing import Callable, Dict, List, TypedDict
import gradio as gr
import os
from gettext import gettext as _
from concurrent.futures import ThreadPoolExecutor
import requests

LOG_PULL_DELAY = 0.5

Deployment = Dict[str, List[Callable]]
"List of functions that define the deployment pipeline"

Executions = Dict[str, List[Callable]]
"List of functions that define the execution pipeline"

class Device(TypedDict, total=False):
    """
    Manifest of devices, their deployements and executions.

    If :param:`name` and/or :param:`address` is not provided, two of the first devices seen by orchestrator are used
    as left and right side devices. If the devices have fixed addresses, it might be better to provide them here.

    :param name: Name of the device, used to identify device in logs
    :param address: Address of the device. Provide as full URL, e.g. `http://1.2.3.4:3000`
    """
    name: str | None
    address: str | None
    deployements: List[Deployment]
    executions: List[Executions]

MANIFESTS: List[Device] = [
    {

        "name": "device_2",
        "address": None,
        "deployements": [
        ],
        "executions": [
        ],
    },
    {

        "name": "device_2",
        "address": "1.2.3.4",
        "deployements": [],
        "executions": [],
    }
]

OLD_MANIFEST = {
    # device names in logs. First is left side, second is right side.
    "devices": [],  # ["device_1", "device_2"],
    "address": [],  # ["1.2.3.4", "1.2.3.5"],
    
}

os.environ.setdefault('GRADIO_ANALYTICS_ENABLED', 'false')
os.environ.setdefault('WASMIOT_ORCHESTRATOR_URL', 'http://localhost:3000')
os.environ.setdefault('WASMIOT_LOGGING_ENDPOINT', f"{os.environ['WASMIOT_ORCHESTRATOR_URL']}/device/logs")

logs_queue = [
    collections.deque(maxlen=100),
    collections.deque(maxlen=100)
]

# Internal logger
logger = logging.getLogger(__name__)

def get_devices():
    """
    Get devices from orchestrator and populate :var:`MANIFESTS` with them.
    """
    global MANIFESTS
    i = 0

    res = requests.get(f"{os.environ['WASMIOT_ORCHESTRATOR_URL']}/file/device")

    if len(MANIFESTS) != 2:
        logger.warning("Expected 2 devices to be defined in :env:`MANIFESTS`, has %d", len(MANIFESTS))

    if data := res.json():
        for device in data:
            if device['name'] == "orchestrator":
                logger.info("Skipping %s, address %s", device['name'], device['communication']['addresses'][0])
                continue

            if i > len(MANIFESTS):
                logger.warning("More devices seen than expected, skipping %d devices", len(MANIFESTS) - i)
                break

            MANIFESTS[i]['name'] = device['name']
            MANIFESTS[i]['address'] = f"http://{device['communication']['addresses'][0]}:{device['communication']['port']}"
            i += 1

    # Check that all devices are defined
    for device in MANIFESTS:
        if not device['name'] or not device['address']:
            logger.error("Device not defined, please define device name and address in :var:`MANIFESTS`")
            return


def pull_logs(orchestrator_logs_url=os.environ.get('WASMIOT_LOGGING_ENDPOINT')):
    """
    Pull logs from orchestrator.
    
    Populates logs_queue with logs from orchestrator.
    """

    global logs_queue

    logs_after = datetime.datetime.now(datetime.UTC)

    if not orchestrator_logs_url:
        raise ValueError("Orchestrator URL is not set, please set WASMIOT_LOGGING_ENDPOINT environment variable")

    logger.debug("Pulling logs after from %s", orchestrator_logs_url)



    while True:
        time.sleep(LOG_PULL_DELAY)
        try:

            # Device mapping to index for logs_queue
            devices = {dev['name']: idx for idx, dev in enumerate(MANIFESTS)}

            res = requests.get(orchestrator_logs_url, params={"after": logs_after.isoformat()})
            if res.ok:
                logs = res.json()
                logger.debug("Received %d logs", len(logs), extra={"logs": logs})

                if not logs: continue

                for log in logs:
                    if log['deviceName'] in devices:
                        idx = devices[log['deviceName']]
                        logs_queue[idx].append(log)
                    else:
                        logger.debug("Unknown device name: %s", log['deviceName'])

                logs_after = datetime.datetime.fromisoformat(logs[-1]['dateReceived'])
        except Exception as e:
            logger.error("Error pulling logs: %s", e, exc_info=True)


def log_reader(idx):
    
    messages = []
    for log in logs_queue[idx]:
        match log:
            case {"message": "Health check done"}:
                log['message'] = "🟢 Health check done"
            case _:
                pass

        messages.append(f"{log['timestamp']} - {log['deviceName']} -  {log['message']}")   
        
    #msgs = [f"{log['timestamp']} - {log['deviceName']} - {log['message']}" for log in logs_queue[idx]]
    return "\n".join(messages)


def reset():
    logs_queue.clear()


def health_check() -> bool:
    """
    Ping all devices and orchestrator for health check.
    """

    time.sleep(1)


    urls = [f"{dev['address']}/health" for dev in MANIFESTS] + [f"{os.environ.get('WASMIOT_ORCHESTRATOR_URL')}/health"]

    def _ping(url):
        # If crashes here, check that the device is accessible and press "reset discovery" in orchestrator
        res = requests.get(url)
        return res.ok

    # run in thread executor pool
    with ThreadPoolExecutor() as executor:
        results = executor.map(_ping, urls)
    
    return all(results)


def app():
    """
    Main application interface
    
    ..todo:: 
        - Niko wants application to show more information
    """
    
    def ping_button(init=False):
        opts = {
            "size": "sm",
        }
        if health_check():
            return gr.Button("Health Check: OK", variant="secondary", **opts)
        else:
            return gr.Button("Health Check: FAIL", variant="stop", **opts)
    
    with gr.Blocks(title=_("WasmIoT Demo")) as _app:
        with gr.Row():
            anim_el = gr.HTML("""<marquee behavior="scroll" direction="left" style="height:200px">Welcome to the WasmIoT Demo</marquee>""")
        with gr.Row() as row:
            def log_reader_left():
                return log_reader(0)
            
            def log_reader_right():
                return log_reader(1)

            dev_left = MANIFESTS[0]['name']
            dev_right = MANIFESTS[1]['name']

            with gr.Column():
                gr.Image(type="filepath", label=_("Upload Image"))
                gr.Dropdown(label=_("Input module"), choices=['foo', 'bar'])

                gr.Textbox(log_reader_left,
                           label=f"{dev_left} log messages",
                           info="Log messages sent by the device",
                           interactive=False,
                           autoscroll=True,
                           lines=4,
                           max_lines=4,
                           every=LOG_PULL_DELAY)

            with gr.Column():
                gr.Image(label=_("Output"))
                gr.Dropdown(label=_("Processing module"), choices=['...'])
                gr.Textbox(log_reader_right, label=f"{dev_right} log messages", interactive=False, autoscroll=True, lines=4, max_lines=4, autofocus=False, every=LOG_PULL_DELAY)


        with gr.Row(variant="panel"):
            btn_deploy = gr.Button("deploy")

            btn_reset = gr.Button("reset")
            btn_reset.click(reset)

            btn_run = gr.Button("run")
            
            btn_ping = ping_button()
            btn_ping.click(ping_button, outputs=[btn_ping])

    return _app

if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    logger.setLevel(logging.DEBUG)

    get_devices()

    threading.Thread(target=pull_logs).start()

    _app = app()
    _app.queue()
    _app.launch()
