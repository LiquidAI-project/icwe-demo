"""
ICWE 2024 Demo setup
====================

Defines the setup for the ICWE 2024 Demo.
"""
import collections
import logging
from typing import List
from ._typing import Device

logger = logging.getLogger(__name__)

def deploy_image_capture():
    """
    Deploy image capture to device.
    """
    logger.info("Deploying image capture")


MANIFESTS: List[Device] = [
    {
        "name": "raspi2",
        "address": "http://172.15.0.22:3000",
        "deployements": {
            "Accuire image": [
                deploy_image_capture,
            ],
        },
        "executions": [
        ],
    },
    {
        "name": "raspi1",
        "address": "http://172.15.0.21:3000",
        "deployements": [],
        "executions": [],
    }
]


logs_queue = [
    collections.deque(maxlen=100),
    collections.deque(maxlen=100)
]
