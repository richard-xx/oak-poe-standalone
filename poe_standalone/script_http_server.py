#!/usr/bin/env python3
# coding=utf-8
import time

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

    # Define a source - color camera
    cam = pipeline.create(dai.node.ColorCamera)
    # VideoEncoder
    jpeg = pipeline.create(dai.node.VideoEncoder)
    jpeg.setDefaultProfilePreset(cam.getFps(), dai.VideoEncoderProperties.Profile.MJPEG)

    # Script node
    script = pipeline.create(dai.node.Script)
    script.setProcessor(dai.ProcessorType.LEON_CSS)
    scrpt_str = Template("""
        from http.server import BaseHTTPRequestHandler
        import socketserver
        import socket
        import fcntl
        import struct

        PORT = ${_PORT}
        ctrl = CameraControl()
        ctrl.setCaptureStill(True)

        def get_ip_address(ifname):
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            return socket.inet_ntoa(fcntl.ioctl(
                s.fileno(),
                -1071617759,  # SIOCGIFADDR
                struct.pack('256s', ifname[:15].encode())
            )[20:24])

        class HTTPHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/':
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b'<h1>[DepthAI] Hello, world!</h1><p>Click <a href="img">here</a> for an image</p>')
                elif self.path == '/img':
                    node.io['out'].send(ctrl)
                    jpegImage = node.io['jpeg'].get()
                    self.send_response(200)
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', str(len(jpegImage.getData())))
                    self.end_headers()
                    self.wfile.write(jpegImage.getData())
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b'Url not found...')

        with socketserver.TCPServer(("", PORT), HTTPHandler) as httpd:
            node.warn(f"Serving at {get_ip_address('re0')}:{PORT}")
            httpd.serve_forever()
    """)
    script.setScript(
        scrpt_str.safe_substitute(_PORT=port)
    )

    # Connections
    cam.still.link(jpeg.input)
    script.outputs["out"].link(cam.inputControl)
    jpeg.bitstream.link(script.inputs["jpeg"])

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
            click.launch(f"http://{device_info.name}:5000")
            while not device.isClosed():
                time.sleep(1)
