from concurrent.futures import ThreadPoolExecutor
import datetime
import logging
import os
import time
from typing import List

import requests

from ._typing import Device
from .settings import settings
from .SETUP import MANIFESTS, logs_queue

logger = logging.getLogger(__name__)


def pull_logs(orchestrator_logs_url=settings.WASMIOT_LOGGING_ENDPOINT, log_pull_delay=settings.LOG_PULL_DELAY):
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
        time.sleep(log_pull_delay)
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


def device_log(msg, *args, device: Device, level=logging.INFO, **kwargs):
    """
    Helper function to log messages with device name.
    """
    device_name = device["name"]
    idx_list = [dev['name'] for dev in MANIFESTS]
    
    if device_name in idx_list:
        idx = idx_list.index(device_name)
        struct_log = {
            "timestamp": datetime.datetime.now().isoformat(),
            "deviceName": device_name,
            "message": msg % args,
            # Other fields?
        }

        # Add log to logs_queue
        logs_queue[idx].append(struct_log)


    return logger.getChild(device_name).log(level, msg, *args, **kwargs)


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


def health_check() -> bool:
    """
    Ping all devices and orchestrator for health check.
    """

    time.sleep(1)


    devices = MANIFESTS + [{
        "name": "orchestrator",
        "address": os.environ.get('WASMIOT_ORCHESTRATOR_URL')
    }]

    def _ping(device: Device):
        # If crashes here, check that the device is accessible and press "reset discovery" in orchestrator
        try:
            url = f"{device['address']}/health"
            device_log("🔍 Health check to %s", url, device=device)
            res = requests.get(url, timeout=3)
        except requests.exceptions.Timeout:
            device_log("🤕 Health check failed: Timeout connecting to %s", url, level=logging.ERROR, device=device)
            return False

        return res.ok


    # run in thread executor pool
    with ThreadPoolExecutor() as executor:
        results = executor.map(_ping, devices)

    return all(results)
