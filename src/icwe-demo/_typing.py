from typing import Any, Callable, Dict, List, TypeAlias, TypedDict

DeviceID: TypeAlias = str
ModuleID: TypeAlias = str
DeploymentID: TypeAlias = str

class Device(TypedDict):
    """
    Manifest of devices, their deployements and executions.

    If :param:`name` and/or :param:`address` is not provided, two of the first devices seen by orchestrator are used
    as left and right side devices. If the devices have fixed addresses, it might be better to provide them here.

    Both :param:`deployements` and :param:`executions` are lists of functions that define the deployment and execution
    pipelines. The functions are called in order.

    :param name: Name of the device, used to identify device in logs
    :param address: Address of the device. Provide as full URL, e.g. `http://1.2.3.4:3000`
    """
    name: str | None
    address: str | None
    _id: DeviceID | None


class Module(TypedDict):
    """
    Module definition.

    :param name: Name of the module
    :param _id: ID of the module
    """
    name: str
    _id: ModuleID


class Deployment(TypedDict):
    name: str
    _id: DeploymentID
