"""
ICWE 2024 Demo setup
====================

Defines the setup for the ICWE 2024 Demo.
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
    },
    {
        "name": "raspi2",
        "address": "http://172.15.0.22:5000",
        "_id": "666d5f52c015bf5d9be90565",
    }
]


MODULES: List[Module] = [

]




DEPLOYMENTS: List[Deployment] = [

]


logs_queue = collections.deque(maxlen=256)
