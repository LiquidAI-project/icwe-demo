import collections
import datetime
import logging
import threading
import time
import gradio as gr
import os
from gettext import gettext as _
from concurrent.futures import ThreadPoolExecutor


import requests

LOG_PULL_DELAY = 0.5

MANIFEST = {
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


def get_devices():
    """
    Get devices from orchestrator
    """
    global MANIFEST

    res = requests.get(f"{os.environ['WASMIOT_ORCHESTRATOR_URL']}/file/device")
    if data := res.json():
        # Ignore first device, it is orchestrator
        for device in data[1:]:
            MANIFEST['devices'].append(device['name'])
            MANIFEST['address'].append(f"http://{device['communication']['addresses'][0]}:{device['communication']['port']}")

    if len(MANIFEST['devices']) != 2:
        logger.warning("Expected 2 devices to be seen by orchestrator %r, got %d", os.environ['WASMIOT_ORCHESTRATOR_URL'], len(MANIFEST['devices']))

    logger.debug("Devices: %s", MANIFEST['devices'])

logger = logging.getLogger(__name__)

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

            res = requests.get(orchestrator_logs_url, params={"after": logs_after.isoformat()})
            if res.ok:
                logs = res.json()
                logger.debug("Received %d logs", len(logs), extra={"logs": logs})

                if not logs: continue

                for log in logs:
                    if log['deviceName'] in MANIFEST['devices']:
                        idx = MANIFEST['devices'].index(log['deviceName'])
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

    urls = [f"{addr}/health" for addr in MANIFEST['address'] + [os.environ.get('WASMIOT_ORCHESTRATOR_URL')]]

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
        if health_check():
            return gr.Button("Health Check: OK", variant="secondary")
        else:
            return gr.Button("Health Check: FAIL", variant="stop")
    
    with gr.Blocks(title=_("WasmIoT Demo")) as _app:
        with gr.Row():
            anim_el = gr.HTML("""<marquee behavior="scroll" direction="left" style="height:200px">Welcome to the WasmIoT Demo</marquee>""")
        with gr.Row() as row:
            def log_reader_left():
                return log_reader(0)
            
            def log_reader_right():
                return log_reader(1)
            
            with gr.Column():
                gr.Image(type="filepath", label=_("Upload Image"))
                gr.Dropdown(label=_("Input module"), choices=['foo', 'bar'])
                gr.Textbox(log_reader_left, label=_("Log messages"), interactive=False, autoscroll=True, lines=4, max_lines=4, autofocus=False, every=LOG_PULL_DELAY)

            with gr.Column():
                gr.Image(label=_("Output"))
                gr.Dropdown(label=_("Processing module"), choices=['...'])
                gr.Textbox(log_reader_right, label=_("Log messages"), interactive=False, autoscroll=True, lines=4, max_lines=4, autofocus=False, every=LOG_PULL_DELAY)


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
