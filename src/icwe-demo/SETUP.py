"""
ICWE 2024 Demo setup
====================

Defines the setup for the ICWE 2024 Demo.

Devices is static list to keep order of devices in the UI. Modules and deployments are updated from the orchestrator on
startup.

..todo::
    - Add mapping for "human descriptions" for modules
"""

import collections
import logging
from typing import List
from ._typing import Device, Module, Deployment

logger = logging.getLogger(__name__)


DEVICES: List[Device] = [
    {
        "name": "raspi1",
        "_id": "666d5f52c015bf5d9be90567",
        "address": "http://172.15.0.21:5000",
        "description": "Edit in SETUP.py: Raspberry Pi 4B with 4GB RAM",
    },
    {
        "name": "raspi2",
        "address": "http://172.15.0.22:5000",
        "_id": "666d5f52c015bf5d9be90565",
        "description": "Description for device 2: Raspberry Pi 4B with 4GB RAM",
    }
]

# Updated by :func:`pull_orchestrator_modules()`
MODULES: List[Module] = []

# Updated by :func:`pull_orchestrator_deployments()`
DEPLOYMENTS: List[Deployment] = []

logs_queue = collections.deque(maxlen=256)
