#!/usr/bin/env python3
# coding=utf-8
import time
from pathlib import Path

import click
import depthai as dai
from loguru import logger
from string import Template
try:
    from poe_standalone.utils import getDeviceInfo
except ImportError:
    from utils import getDeviceInfo


def create_pipeline(port=5000, blob_path=None, config_path=None, host_ip=None):
    # Start defining a pipeline
    pipeline = dai.Pipeline()

    # Script node
    script = pipeline.create(dai.node.Script)
    script.setProcessor(dai.ProcessorType.LEON_CSS)

    scrpt_str = Template("""
'''
import random
import re
import socket
import struct
from socket import AF_UNSPEC, SOCK_STREAM
from socketserver import BaseRequestHandler, ThreadingTCPServer
from threading import Event, Lock, Thread
'''
${_pyModbusTCP}
import socketserver
import fcntl
import struct
import time
PORT = ${_PORT}

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        -1071617759,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15].encode())
    )[20:24])
    
class MyDataBank(DataBank):

    def on_coils_change(self, address, from_value, to_value, srv_info):
        msg = 'change in coil space [{0!r:^5} > {1!r:^5}] at @ 0x{2:04X} from ip: {3:<15}'
        msg = msg.format(from_value, to_value, address, srv_info.client.address)
        node.warn(msg)

    def on_holding_registers_change(self, address, from_value, to_value, srv_info):
        msg = 'change in hreg space [{0!r:^5} > {1!r:^5}] at @ 0x{2:04X} from ip: {3:<15}'
        msg = msg.format(from_value, to_value, address, srv_info.client.address)
        node.warn(msg)

server = ModbusServer(host="", port=PORT, no_block=True, data_bank=MyDataBank())
node.warn(f"ModbusServer at {get_ip_address('re0')}:{PORT}")
server.start()
while 1:
    server.data_bank.set_holding_registers(0, [int(time.time()) % (24*3600) // 10])
    time.sleep(5)
    """)
    script.setScript(
        scrpt_str.safe_substitute(_PORT=port, _pyModbusTCP=(Path(__file__).parent / "pyModbusTCP.py").read_text())
    )

    return pipeline


if __name__ == "__main__":
    with logger.catch():
        # Connect to device with pipeline
        device_info = getDeviceInfo()
        with dai.Device(create_pipeline(port=5000, blob_path=None, config_path=None, host_ip=None), device_info) as device:
            click.echo(f"\t>>> Name: {device_info.name}")
            click.echo(f"\t>>> MXID: {device.getMxId()}")
            click.echo(f"\t>>> Cameras: {[c.name for c in device.getConnectedCameras()]}")
            click.echo(f"\t>>> USB speed: {device.getUsbSpeed().name}")
            while not device.isClosed():
                time.sleep(1)
