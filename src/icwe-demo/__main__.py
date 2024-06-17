from pathlib import Path
import threading

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn
from .ui import gradio_app
from .utils import pull_orchestrator_deployments, pull_orchestrator_devices, pull_logs, pull_orchestrator_modules
import logging
from rich.logging import RichHandler
import gradio as gr

logger = logging.getLogger(__package__)

if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        format=r"%(message)s",
        datefmt=r"[%X]",
        handlers=[RichHandler(rich_tracebacks=True)]
    )
    logger.setLevel(logging.DEBUG)

    logger.info("Pulling orchestrator devices, modules and deployments...")
    #pull_orchestrator_devices()
    pull_orchestrator_modules()
    pull_orchestrator_deployments()

    logger.info("Starting log puller...")
    threading.Thread(target=pull_logs).start()

    gr_app = gradio_app()
    gr_app.queue()

    app = FastAPI()

    static_dir = Path("./figures")
    print(static_dir.absolute())
    app.mount("/figures", StaticFiles(directory=static_dir), name="figures")

    app = gr.mount_gradio_app(app, gr_app, path="/")

    #print(gr_app.launch())
    logger.info("Starting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=7860)
