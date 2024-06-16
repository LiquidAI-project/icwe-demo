import threading
from .ui import app
from .utils import get_devices, pull_logs
import logging
import rich
from rich.logging import RichHandler

logger = logging.getLogger(__name__)

if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        handlers=[RichHandler(rich_tracebacks=True)]
    )
    logger.setLevel(logging.DEBUG)

    get_devices()

    threading.Thread(target=pull_logs).start()

    _app = app()
    _app.queue()
    _app.launch()
