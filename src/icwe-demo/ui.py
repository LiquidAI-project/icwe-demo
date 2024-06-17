"""
UI for WasmIoT demo.
====================
"""

import collections
import datetime
import logging
import random
import re
import threading
import time
from typing import Callable, Iterator, List, Literal, Tuple
import gradio as gr
import os
from gettext import gettext as _
import requests

from ._typing import Device
from .settings import settings
from .SETUP import DEVICES, DEPLOYMENTS, logs_queue
from .utils import do_deployment, find_deployment_solution, get_modules, health_check, run_deployment

labels_path = os.path.join(os.path.dirname(__file__), "labels.txt")
labels = open(labels_path).read().splitlines()

os.environ.setdefault('GRADIO_ANALYTICS_ENABLED', 'false')

# Internal logger
logger = logging.getLogger(__name__)

# Pool of outgoing chat messages. See: https://www.gradio.app/docs/gradio/chatbot#behavior
chat_history = collections.deque(maxlen=15)

# Precompiled regexes for log parsing
RE_WASM_PREPARE = re.compile(r"Preparing Wasm module '(?P<module_name>.+)'")
RE_WASM_FUNC_RUN = re.compile(r"Running Wasm function '(?P<function_name>.+)'")
RE_DEPLOY_MODULE = re.compile(r"Deploying module '(?P<module_name>.+)'")

RE_RESULT_URL = re.compile(r"Result url: (?P<url>.+)")

log_history = [
    collections.deque(maxlen=100),
    collections.deque(maxlen=100)
]

def download_image(url, save_path):
    response = requests.get(url, stream=True)
    response.raise_for_status()  # Ensure we got a successful response

    with open(save_path, 'wb') as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)

def device_event(idx: Literal[0, 1, -1], msg = str | Tuple[str, str|None]):
    """
    New device message for displaying in the chat.

    :param idx: Index of the device. 0 for left, 1 for right, -1 for both.
    :param msg: Message to display. If a tuple, the first element is the image URL, the second is the text.
    """
    if isinstance(msg, str):
        # Check if the message is a URL
        if re.match(r"^https?://.*\.(png|jpg|jpeg|gif)\??.*$", msg) or re.match(r"tmp/.*\.(png|jpg|jpeg|gif)$", msg):
            msg = (msg, None)

    match idx:
        case -1:
            chat_history.append([msg, msg])
        case 0:
            chat_history.append([None, msg])
        case 1:
            chat_history.append([msg, None])


def log_parser():
    """
    Read logs from the queue and sort them for display.
    """
    devices = {dev['name']: idx for idx, dev in enumerate(DEVICES)}

    # Process all new lines
    while logs_queue:
        log = logs_queue.popleft()

        idx = devices[log['deviceName']]

        match log:
            case {"message": "Health check done"}:
                log['message'] = "🩺 " + log['message']
            case {"message": "Deployment created"}:
                log['message'] = "🚀 " + log['message']

                match idx:
                    case 0:
                        device_event(0, f"{settings.DEMO_URL}/figures/orch2raspi1.gif")
                    case 1:
                        device_event(1, f"{settings.DEMO_URL}/figures/orch2raspi2.gif")

                device_event(idx, "🚀 Deployment sent to IoT device")

            case {"message": "Module run"}:
                log['message'] = "⚙️ " + log['message']

            case _:
                if re.match(RE_WASM_PREPARE, log['message']):
                    log['message'] = "📦 " + log['message']
                    device_event(idx, log['message'])

                elif re.match(RE_WASM_FUNC_RUN, log['message']):
                    log['message'] = "λ " + log['message']
                    device_event(idx, log['message'])
                elif re.match(RE_DEPLOY_MODULE, log['message']):
                    log['message'] = "🚚 " + log['message']
                    device_event(idx, log['message'])
                elif grp := re.match(RE_RESULT_URL, log['message']):
                    filepath = f"tmp/result_{idx}_{datetime.datetime.now().timestamp()}.jpeg"
                    download_image(log['message'][12:], filepath)
                    device_event(idx, filepath)
                    # Use tuple to force image display in chat
                    #cachebuster_url = f"{grp['url']}?t={datetime.datetime.now().timestamp()!s}"
                    #device_event(idx, (cachebuster_url, log['message']))
                elif re.match(r"Execution result: .*", log['message']):
                    # Parse numeric result class to textual label
                    result_class = labels[int(log['message'][17:]) - 1]
                    device_event(idx, result_class)

                else:
                    # Unhandled log message
                    # If the first character is not emoji character, use log level to set emoji
                    _ord = ord(log['message'][0])
                    if _ord <= 256:
                        match log['loglevel']:
                            case 'INFO':
                                log['message'] = "ℹ️ " + log['message']
                            case 'ERROR':
                                log['message'] = "🔴 " + log['message']
                            case 'WARNING':
                                log['message'] = "⚠️ " + log['message']
                            case 'DEBUG':
                                log['message'] = "🐞 " + log['message']
                            case _:
                                logger.debug("Unknown log level: %s", log['level'])

        # Format time with ms
        time = datetime.datetime.fromisoformat(log['timestamp']).strftime("%H:%M:%S.%f")[:-3]
        log_history[idx].append(f"[{time}] {log['message']}")
        logger.getChild(f"device-{log['deviceName']}").log(logging.DEBUG, f"[{log['deviceName']}]: {log['message']}")


def log_reader(idx):
    log_parser()
    return "\n".join(log_history[idx])


def reset():
    raise NotImplementedError("Reset not implemented")
    logs_queue.clear()

    return (
        gr.Image(None, interactive=False),
        gr.Image(None, interactive=False)
    )

def test_chatbot_yielding():
    history = []

    while len(chat_history):
        time.sleep(settings.STEP_DELAY)
        history.append(chat_history.popleft())
        yield history


def ping_button(init=False):
    opts = {
        "size": "sm",
    }
    if health_check():
        return gr.Button("Health: 🙂", variant="secondary", **opts)
    else:
        return gr.Button("Health: 🤕", variant="stop", **opts)


def deploy(module_left, module_right):
    logger.debug("Deploying modules %s and %s", module_left, module_right)
    deployment = find_deployment_solution(module_left, module_right)
    if deployment is None:
        raise gr.Error("No deployment solution found")

    device_event(-1, f"🚚 Preparing to deploy")

    do_deployment(deployment)


def do_run(module_left, module_right):
    logger.debug("Running modules %s and %s", module_left, module_right)
    deployment = find_deployment_solution(module_left, module_right)
    if deployment is None:
        raise gr.Error("No deployment found")

    device_event(-1, f"🚀 Running deployment")

    run_deployment(deployment)


def wobbly_delay(delay: float = settings.STEP_DELAY):
    """
    Sleep for a random amount of time to make the UI more lively.
    """
    time.sleep(random.uniform(0.5, 1.5) * delay)


def run_yielding(target: Callable, args: Tuple) -> Iterator:
    """
    Perform a blocking operation in the background and yield the results.
    """

    # Start in background task, as it's blocking
    task = threading.Thread(target=target, args=args)
    task.start()

    msgs = []
    while True:
        if len(chat_history) == 0 and not task.is_alive():
            logger.debug("Task %s finished", target.__name__)
            break

        if len(chat_history) > 0:
            yield chat_history.popleft()
            wobbly_delay()
        else:
            # Wait for the task to finish
            time.sleep(settings.LOG_PULL_DELAY)



def gradio_app():
    """
    Main application interface
    
    ..todo:: 
        - Niko wants application to show more information
    """

    LOG_PULL_DELAY = settings.LOG_PULL_DELAY

    modules = get_modules()

    with gr.Blocks(title=_("WasmIoT ICWE Demo"), theme=gr.themes.Monochrome()) as _app:

        with gr.Row():
            eventlog = gr.Chatbot([], label="Results", bubble_full_width=False)

        with gr.Row() as row:
            def log_reader_left():
                return log_reader(0)
            
            def log_reader_right():
                return log_reader(1)

            dev_left = DEVICES[0]['name']
            dev_right = DEVICES[1]['name']

            with gr.Column():
                gr.HTML(f"<h2>{dev_left}</h2><div class='text-muted'>{DEVICES[0]['description']}</div>")

                module_left = gr.Dropdown(label=f"{dev_left} module", choices=modules)

                gr.Textbox(log_reader_left,
                           label=f"{dev_left} log messages",
                           info="Log messages sent by the device",
                           interactive=False,
                           autoscroll=True,
                           lines=4,
                           max_lines=4,
                           every=LOG_PULL_DELAY)

            with gr.Column():
                gr.HTML(f"<h2>{dev_right}</h2><div class='text-muted'>{DEVICES[1]['description']}</div>")

                module_right = gr.Dropdown(label=f"{dev_right} module", choices=modules)

                gr.Textbox(log_reader_right,
                           label=f"{dev_right} log messages",
                           info="Log messages sent by the device",
                           interactive=False,
                           autoscroll=True,
                           lines=4,
                           max_lines=4,
                           every=LOG_PULL_DELAY)

        with gr.Row(variant="panel"):

            def deploy_btn(btn, module_left, module_right):
                msgs = []
                for msg in run_yielding(target=deploy, args=(module_left, module_right)):
                    msgs.append(msg)
                    yield gr.Button("🔨 Deploying...", interactive=False), msgs

                yield gr.Button(btn, interactive=True), msgs

            def run_btn(btn, module_left, module_right):
                msgs = []
                for msg in run_yielding(target=do_run, args=(module_left, module_right)):
                    msgs.append(msg)
                    yield gr.Button("⚙️ Running...", interactive=False), msgs

                yield gr.Button(btn, interactive=True), msgs

            btn_deploy = gr.Button("Deploy")
            btn_deploy.click(deploy_btn, inputs=[btn_deploy, module_left, module_right], outputs=[btn_deploy, eventlog])

            btn_run = gr.Button("Run")
            btn_run.click(run_btn, inputs=[btn_run, module_left, module_right], outputs=[btn_run, eventlog])

            btn_reset = gr.Button("Reset", size="sm", variant="secondary")
            btn_reset.click(reset)

            btn_ping = ping_button(init=True)
            btn_ping.click(ping_button, outputs=[btn_ping])

    return _app

