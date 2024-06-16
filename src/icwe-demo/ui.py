"""
UI for WasmIoT demo.
====================

To define workflows, see :var:`MANIFESTS`.

"""

import collections
import datetime
import logging
import threading
import time
import gradio as gr
import os
from gettext import gettext as _
import requests

from ._typing import Device
from .settings import settings
from .SETUP import MANIFESTS, logs_queue
from .utils import health_check

os.environ.setdefault('GRADIO_ANALYTICS_ENABLED', 'false')


# Internal logger
logger = logging.getLogger(__name__)


def log_reader(idx):
    messages = []
    for log in logs_queue[idx]:
        match log:
            case {"message": "Health check done"}:
                log['message'] = "⚕️ Health check done"
            case _:
                # If the first character is not emoji character, use log level to set emoji
                _ord = ord(log['message'][0])
                if _ord <= 256:
                    match log['level']:
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

        messages.append(f"[{time}] {log['message']}")
        
    #msgs = [f"{log['timestamp']} - {log['deviceName']} - {log['message']}" for log in logs_queue[idx]]
    return "\n".join(messages)


def reset():
    logs_queue.clear()

    return (
        gr.Image(None, interactive=False)
    )


def app():
    """
    Main application interface
    
    ..todo:: 
        - Niko wants application to show more information
    """

    LOG_PULL_DELAY = settings.LOG_PULL_DELAY

    def ping_button(init=False):
        opts = {
            "size": "sm",
        }
        if health_check():
            return gr.Button("Health: 🙂", variant="secondary", **opts)
        else:
            return gr.Button("Health: 🤕", variant="stop", **opts)
    
    with gr.Blocks(title=_("WasmIoT ICEW Demo"), theme=gr.themes.Monochrome()) as _app:
        with gr.Row():
            # Visualization row
            anim_el = gr.HTML("""<marquee behavior="scroll" direction="left" style="height:200px">Welcome to the WasmIoT Demo</marquee>""")
        with gr.Row() as row:
            def log_reader_left():
                return log_reader(0)
            
            def log_reader_right():
                return log_reader(1)

            dev_left = MANIFESTS[0]['name']
            dev_right = MANIFESTS[1]['name']

            with gr.Column():
                gr.HTML(f"<h2>{dev_left}</h2>")
                left_image = gr.Image(label=_("Result"))
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
                gr.HTML(f"<h2>{dev_right}</h2>")
                right_image = gr.Image(label=_("Result"))
                gr.Dropdown(label=_("Processing module"), choices=['...'])

                gr.Textbox(log_reader_right,
                           label=f"{dev_left} log messages",
                           info="Log messages sent by the device",
                           interactive=False,
                           autoscroll=True,
                           lines=4,
                           max_lines=4,
                           every=LOG_PULL_DELAY)

        with gr.Row(variant="panel"):
            btn_deploy = gr.Button("Deploy")
            btn_run = gr.Button("Run")

            btn_reset = gr.Button("Reset", size="sm", variant="secondary")
            btn_reset.click(reset, outputs=[left_image, right_image])
            
            btn_ping = ping_button(init=True)
            btn_ping.click(ping_button, outputs=[btn_ping])

    return _app

