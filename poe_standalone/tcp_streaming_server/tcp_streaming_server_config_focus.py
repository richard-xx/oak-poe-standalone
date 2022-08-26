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
    # Start defining a pipeline
    pipeline = dai.Pipeline()

    camRgb = pipeline.createColorCamera()
    camRgb.setIspScale(2, 3)

    videoEnc = pipeline.create(dai.node.VideoEncoder)
    videoEnc.setDefaultProfilePreset(30, dai.VideoEncoderProperties.Profile.MJPEG)
    camRgb.video.link(videoEnc.input)

    script = pipeline.create(dai.node.Script)
    script.setProcessor(dai.ProcessorType.LEON_CSS)

    videoEnc.bitstream.link(script.inputs['frame'])
    script.inputs['frame'].setBlocking(False)
    script.inputs['frame'].setQueueSize(1)

    script.outputs['control'].link(camRgb.inputControl)
    scrpt_str = Template("""
    import socket
    import time
    import threading
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", ${_PORT}))
    server.listen()
    node.warn("Server up port: ${_PORT}")
    def send_frame_thread(conn):
        try:
            while True:
                pck = node.io["frame"].get()
                data = pck.getData()
                ts = pck.getTimestamp()
                header = f"ABCDE " + str(ts.total_seconds()).center(18) + str(len(data)).center(8)
                # node.warn(f'>{header}<')
                conn.send(bytes(header, encoding='ascii'))
                conn.send(data)
        except Exception as e:
            node.warn("Client disconnected")
    def receive_msgs_thread(conn):
        try:
            while True:
                data = conn.recv(32)
                txt = str(data, encoding="ascii")
                vals = txt.split(',')
                ctrl = CameraControl(100)
                ctrl.setManualFocus(int(vals[0]))
                node.io['control'].send(ctrl)
        except Exception as e:
            node.warn("Client disconnected")
    while True:
        conn, client = server.accept()
        node.warn(f"Connected to client IP: {client}")
        threading.Thread(target=send_frame_thread, args=(conn,)).start()
        threading.Thread(target=receive_msgs_thread, args=(conn,)).start()
    """)
    script.setScript(
        scrpt_str.safe_substitute(_PORT=port)
    )
    return pipeline


if __name__ == '__main__':
    # Connect to device with pipeline
    device_info = getDeviceInfo()
    with dai.Device(create_pipeline(port=5000, blob_path=None, config_path=None, host_ip=None), device_info) as device:
        click.echo(f"\t>>> Name: {device_info.name}")
        click.echo(f"\t>>> MXID: {device.getMxId()}")
        click.echo(f"\t>>> Cameras: {[c.name for c in device.getConnectedCameras()]}")
        click.echo(f"\t>>> USB speed: {device.getUsbSpeed().name}")

        with open("ip.txt", "w") as f:
            f.write(device_info.name)
        while not device.isClosed():
            time.sleep(1)
