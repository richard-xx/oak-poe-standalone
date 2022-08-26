# coding=utf-8
import time
from string import Template

import click
import depthai as dai

try:
    from poe_standalone.utils import getDeviceInfo
except ImportError:
    from utils import getDeviceInfo


def create_pipeline(port=5000, blob_path=None, config_path=None, host_ip=None):
    pipeline = dai.Pipeline()

    camRgb = pipeline.createColorCamera()
    camRgb.setIspScale(2, 3)

    videoEnc = pipeline.create(dai.node.VideoEncoder)
    videoEnc.setDefaultProfilePreset(30, dai.VideoEncoderProperties.Profile.MJPEG)
    camRgb.video.link(videoEnc.input)

    script = pipeline.create(dai.node.Script)
    script.setProcessor(dai.ProcessorType.LEON_CSS)
    videoEnc.bitstream.link(script.inputs["frame"])

    scrpt_str = Template(f"""
    # Enter your own IP!
    HOST_IP = ${_host_ip}
    import socket
    import time
    sock = socket.socket()
    sock.connect((HOST_IP, ${_PORT}))
    while True:
        pck = node.io["frame"].get()
        data = pck.getData()
        ts = pck.getTimestamp()
        header = f"ABCDE " + str(ts.total_seconds()).ljust(18) + str(len(data)).ljust(8)
        # node.warn(f'>{header}<')
        sock.send(bytes(header, encoding='ascii'))
        sock.send(data)
    """)
    script.setScript(
        scrpt_str.safe_substitute(_PORT=port, _host_ip=host_ip)
    )
    return pipeline


if __name__ == "__main__":
    # Connect to device with pipeline
    device_info = getDeviceInfo()
    with dai.Device(create_pipeline(port=5000, blob_path=None, config_path=None, host_ip=None), device_info) as device:
        click.echo(f"\t>>> Name: {device_info.name}")
        click.echo(f"\t>>> MXID: {device.getMxId()}")
        click.echo(f"\t>>> Cameras: {[c.name for c in device.getConnectedCameras()]}")
        click.echo(f"\t>>> USB speed: {device.getUsbSpeed().name}")

        while not device.isClosed():
            time.sleep(1)
