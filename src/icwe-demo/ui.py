import logging
import gradio as gr
import os
from gettext import gettext as _

os.environ.setdefault('GRADIO_ANALYTICS_ENABLED', 'false')

logger = logging.getLogger(__name__)


def app():
    with gr.Blocks(title=_("WasmIoT Demo")) as app:
        with gr.Row() as row:
            with gr.Column():
                gr.Image(type="filepath", label=_("Uplgoad Image"))
                gr.Dropdown(label=_("Input module"), choices=['foo', 'bar'])

            with gr.Column():
                gr.Image(label=_("Output"))
                gr.Dropdown(label=_("Processing module"), choices=['...'])

        with gr.Row():
            gr.Button("deploy")
            gr.Button("reset")
            gr.Button("run")

    return app

if __name__ == "__main__":

    _app = app()
    _app.queue()
    _app.launch()
