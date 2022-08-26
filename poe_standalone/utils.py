# coding=utf-8

import importlib.util
import socket
import sys
from ipaddress import IPv4Address

import depthai as dai
from validators.ip_address import ipv4


def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    local_ip = s.getsockname()[0]
    s.close()
    return local_ip


def lazy_import(name, path=None):
    spec = importlib.util.spec_from_file_location(name, path)
    loader = importlib.util.LazyLoader(spec.loader)
    spec.loader = loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def getDeviceInfo(deviceId=None, debug=False) -> dai.DeviceInfo:
    """
    Find a correct :obj:`depthai.DeviceInfo` object, either matching provided :code:`deviceId` or selected by the user (if multiple devices available)
    Useful for almost every app where there is a possibility of multiple devices being connected simultaneously
    Args:
        deviceId (str, optional): Specifies device MX ID, for which the device info will be collected
    Returns:
        depthai.DeviceInfo: Object representing selected device info
    Raises:
        RuntimeError: if no DepthAI device was found or, if :code:`deviceId` was specified, no device with matching MX ID was found
        ValueError: if value supplied by the user when choosing the DepthAI device was incorrect
    """
    # deviceInfos = []

    if deviceId:
        found, deviceInfo = dai.Device.getDeviceByMxId(deviceId)

        if found:
            if ipv4(deviceInfo.name):
                return deviceInfo
            else:
                raise RuntimeError(f"{deviceId} is not a poe series device !")
        else:
            print(f"Warning! No DepthAI device found with id matching {deviceId} !")

    if debug:
        deviceInfos = dai.XLinkConnection.getAllConnectedDevices()
    else:
        deviceInfos = dai.Device.getAllAvailableDevices()

    deviceInfos = [deviceInfo for deviceInfo in deviceInfos if ipv4(deviceInfo.name)]
    deviceInfos.sort(key=lambda device_info: int(IPv4Address(device_info.name)))

    if len(deviceInfos) == 0:
        raise RuntimeError("No DepthAI device found!")
    else:
        print("Available devices:")
        for i, deviceInfo in enumerate(deviceInfos):
            print(
                f"[{i}] {deviceInfo.name} {deviceInfo.getMxId()} [{deviceInfo.state.name}]"
            )

        if len(deviceInfos) == 1:
            return deviceInfos[0]
        else:
            val = input("Which DepthAI Device you want to use : [0]")
            if val == "":
                val = 0

            return deviceInfos[val]
