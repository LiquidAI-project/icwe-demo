import collections
import datetime
import logging
import threading
import time
import gradio as gr
import os
from gettext import gettext as _

import requests

os.environ.setdefault('GRADIO_ANALYTICS_ENABLED', 'false')
os.environ.setdefault('WASMIOT_ORCHESTRATOR_URL', 'http://localhost:3000')
os.environ.setdefault('WASMIOT_LOGGING_ENDPOINT', f"{os.environ.get('WASMIOT_ORCHESTRATOR_URL')}/device/logs")

LOG_PULL_DELAY = 0.5
#LOG_PULL_DELAY = 2

logs_queue = collections.deque(maxlen=100)

logger = logging.getLogger(__name__)

def pull_logs(orchestrator_logs_url=os.environ.get('WASMIOT_LOGGING_ENDPOINT')):
    """
    Pull logs from orchestrator
    """

    global logs_queue

    logs_after = datetime.datetime.now(datetime.UTC)

    if not orchestrator_logs_url:
        raise ValueError("Orchestrator URL is not set, please set WASMIOT_LOGGING_ENDPOINT environment variable")

    logger.debug("Pulling logs after from %s", orchestrator_logs_url)

    while True:
        time.sleep(LOG_PULL_DELAY)
        res = requests.get(orchestrator_logs_url, params={"after": logs_after.isoformat()})
        if res.ok:
            logs = res.json()
            logger.debug("Received %d logs", len(logs), extra={"logs": logs})

            if not logs: continue

            logs_queue.extend(logs)
            logs_after = datetime.datetime.fromisoformat(logs[-1]['dateReceived'])
        print(res)

    #
    # logs_queue.extend(logs)

def log_reader():
    #pull_logs()
    return "\n".join([f"{log['timestamp']} - {log['deviceName']} - {log['message']}" for log in logs_queue])

def reset():
    logs_queue.clear()

def app():
    """
    Main application interface
    
    ..todo:: 
        - Niko wants application to show more information
    """
    with gr.Blocks(title=_("WasmIoT Demo")) as _app:
        with gr.Row():
            anim_el = gr.HTML("""<marquee behavior="scroll" direction="left" style="height:200px">Welcome to the WasmIoT Demo</marquee>""")
        with gr.Row() as row:
            with gr.Column():
                gr.Image(type="filepath", label=_("Upload Image"))
                gr.Dropdown(label=_("Input module"), choices=['foo', 'bar'])
                logbox = gr.Textbox(log_reader, label=_("Log messages"), interactive=False, autoscroll=True, lines=4, max_lines=4, autofocus=False, every=LOG_PULL_DELAY)
                logbox.submit(log_reader)

            with gr.Column():
                gr.Image(label=_("Output"))
                gr.Dropdown(label=_("Processing module"), choices=['...'])

        with gr.Row():
            gr.Button("deploy")
            btn_reset = gr.Button("reset")
            btn_reset.click(reset)
            gr.Button("run")

    return _app

if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    logger.setLevel(logging.DEBUG)

    threading.Thread(target=pull_logs).start()

    _app = app()
    _app.queue()
    _app.launch()
