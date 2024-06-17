from concurrent.futures import ThreadPoolExecutor
import datetime
import logging
import os
import time
from typing import List, Tuple

import requests
import gradio as gr

from ._typing import Device, Deployment, ModuleID, DeviceID
from .settings import settings
from .SETUP import DEVICES, MODULES, DEPLOYMENTS, logs_queue

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

    devices = [dev['name'] for dev in DEVICES]

    while True:
        time.sleep(log_pull_delay)
        try:
            res = requests.get(orchestrator_logs_url, params={"after": logs_after.isoformat()})
            if res.ok:
                logs = res.json()

                if not logs: continue

                logger.debug("Received %d logs starting from %s", len(logs), logs_after, extra={"logs": logs})

                for log in logs:
                    if log['deviceName'] in devices:
                        logs_queue.append(log)
                    else:
                        logger.debug("Unknown device name: %s", log['deviceName'])

                logs_after = datetime.datetime.fromisoformat(logs[-1]['dateReceived'])
        except Exception as e:
            logger.error("Error pulling logs: %s", e, exc_info=True)


def device_log(msg, *args, device: Device | DeviceID, level=logging.INFO, **kwargs):
    """
    Helper function to log messages with device name.

    ..todo::
        - Fix the stack trace to point to the correct line in the code
    """
    if isinstance(device, DeviceID):
        for idx, dev in enumerate(DEVICES):
            if dev['_id'] == device:
                device_name = dev['name']
                break
        else:
            raise ValueError(f"Device with id {device} not found")
    else:
        device_name = device["name"]

    idx_list = [dev['name'] for dev in DEVICES]

    if device_name in idx_list:
        idx = idx_list.index(device_name)
        struct_log = {
            "timestamp": datetime.datetime.now().isoformat(),
            "deviceName": device_name,
            "message": msg % args,
            # Other fields?
        }

        # Add log to logs_queue
        logs_queue.append(struct_log)

    logger.getChild(f"device_log.{device_name}").log(level, msg, *args, **kwargs)


def pull_orchestrator_devices():
    """
    Get devices from orchestrator and populate :var:`MANIFESTS` with them.
    """

    raise NotImplementedError("This function is not up to date.")
    global DEVICES
    i = 0


    if len(DEVICES) != 2:
        logger.warning("Expected 2 devices to be defined in :env:`MANIFESTS`, has %d", len(DEVICES))


    # Check if MANIFESTS has all the addresses already
    if all(dev['address'] for dev in DEVICES):
        return

    devices_url = f"{settings.WASMIOT_ORCHESTRATOR_URL}/file/device"

    logger.info("Getting devices for manifest from orchestrator %r", devices_url)

    res = requests.get()
    if data := res.json():
        for device in data:
            if device['name'] == "orchestrator":
                logger.info("Skipping %s, address %s", device['name'], device['communication']['addresses'][0])
                continue

            if i > len(DEVICES):
                logger.warning("More devices seen than expected, skipping %d devices", len(DEVICES) - i)
                break

            DEVICES[i]['name'] = device['name']
            DEVICES[i]['address'] = f"http://{device['communication']['addresses'][0]}:{device['communication']['port']}"
            i += 1

    # Check that all devices are defined
    for device in DEVICES:
        if not device['name'] or not device['address']:
            logger.error("Device not defined, please define device name and address in :var:`MANIFESTS`")
            return


def pull_orchestrator_modules():
    global MODULES
    url = f"{settings.WASMIOT_ORCHESTRATOR_URL}/file/module"
    res = requests.get(url)
    if data := res.json():
        MODULES = data
        logger.info("Got %d modules from %s", len(MODULES), url)
    else:
        raise ValueError(f"Error getting modules from {url}")


def pull_orchestrator_deployments():
    """
    Get deployments from orchestrator.
    """
    global DEPLOYMENTS
    deployments_url = f"{settings.WASMIOT_ORCHESTRATOR_URL}/file/manifest"
    res = requests.get(deployments_url)
    if data := res.json():
        DEPLOYMENTS = data
        logger.info("Got %d deployments from %s", len(DEPLOYMENTS), deployments_url)
    else:
        raise ValueError(f"Error getting deployments from {deployments_url}")


def get_modules() -> List[Tuple[str, ModuleID]]:
    """
    Get modules that are used by deployments.

    :return: List of tuples with module name and module id
    """
    global DEPLOYMENTS, MODULES

    # Generate mapping of module id's to module names
    module_map = {module['_id']: module['name'] for module in MODULES}

    devices = [dev['_id'] for dev in DEVICES]

    modules = set()
    for deployment in DEPLOYMENTS:
        for sequence in deployment['sequence']:
            if sequence['module'] not in module_map:
                logger.error("Module %s not found in module list when processing deployment %s", sequence['module'], deployment['_id'])
                continue
            if sequence['device'] not in devices:
                logger.error("Device %s not found in device list when processing deployment %s", sequence['device'], deployment['_id'])
                continue

            modules.add((module_map[sequence['module']], sequence['module']))
    
    return list(modules)


def find_deployment_solution(module_left: ModuleID, module_right: ModuleID) -> Deployment | None:
    """
    Find a deployment that uses the given modules.

    :param module_left: ID of the module used on the left device
    :param module_right: ID of the module used on the right device
    """
    global DEPLOYMENTS

    for deployment in DEPLOYMENTS:
        sequence = deployment['sequence']
        if len(sequence) != 2:
            logger.warning("Deployment %s has %d sequences, expected 2", deployment['_id'], len(sequence))
            continue

        if sequence[0]['module'] == module_left and sequence[1]['module'] == module_right:
            logger.info("Found deployment %s for modules %s and %s", deployment['_id'], module_left, module_right)
            return deployment

    logger.warning("No deployment found for modules %s and %s", module_left, module_right)
    return None


def do_deployment(deployment: Deployment):
    module_names = {module['_id']: module['name'] for module in MODULES}

    left = deployment['sequence'][0]
    right = deployment['sequence'][1]

    device_log("🚚 Deploying module %r", module_names[left['module']], device=left['device'])
    device_log("🚚 Deploying module %r", module_names[right['module']], device=right['device'])

    logger.info("Deploying solution %s", deployment['name'])

    res = requests.post(f"{settings.WASMIOT_ORCHESTRATOR_URL}/file/manifest/{deployment['_id']}", data={
        "id": deployment['_id']
    })

    if not res.ok:
        logger.error("Error deploying solution %s: %s", deployment['name'], res.text)
        raise gr.Error("Error deploying solution: %s", res.text)

    json = res.json()
    device_log("🚚 Orchestrator received device response: %r", json['deviceResponses'][left['device']]['data']['status'], device=left['device'])
    device_log("🚚 Orchestrator received device response: %r", json['deviceResponses'][right['device']]['data']['status'], device=right['device'])



def health_check() -> bool:
    """
    Ping all devices and orchestrator for health check.
    """

    devices = DEVICES + [{
        "name": "orchestrator",
        "address": os.environ.get('WASMIOT_ORCHESTRATOR_URL')
    }]

    def _ping(device: Device):
        # If crashes here, check that the device is accessible and press "reset discovery" in orchestrator
        try:
            url = f"{device['address']}/health"
            device_log("🩺 Health check to %s", url, device=device)
            res = requests.get(url, timeout=3)
        except requests.exceptions.Timeout:
            device_log("🤕 Health check failed: Timeout connecting to %s", url, level=logging.ERROR, device=device)
            return False

        return res.ok


    # run in thread executor pool
    with ThreadPoolExecutor() as executor:
        results = executor.map(_ping, devices)

    return all(results)
