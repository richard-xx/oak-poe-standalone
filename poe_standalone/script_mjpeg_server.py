#!/usr/bin/env python3
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

    # Define a source - color camera
    cam = pipeline.create(dai.node.ColorCamera)
    # VideoEncoder
    jpeg = pipeline.create(dai.node.VideoEncoder)
    jpeg.setDefaultProfilePreset(cam.getFps(), dai.VideoEncoderProperties.Profile.MJPEG)

    # Script node
    script = pipeline.create(dai.node.Script)
    script.setProcessor(dai.ProcessorType.LEON_CSS)

    scrpt_str = Template("""
        import time
        import socket
        import fcntl
        import struct
        from socketserver import ThreadingMixIn
        from http.server import BaseHTTPRequestHandler, HTTPServer
    
        PORT = ${_PORT}
    
        def get_ip_address(ifname):
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            return socket.inet_ntoa(fcntl.ioctl(
                s.fileno(),
                -1071617759,  # SIOCGIFADDR
                struct.pack('256s', ifname[:15].encode())
            )[20:24])
    
        class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
            pass
    
        class HTTPHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/':
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b'<h1>[DepthAI] Hello, world!</h1><p>Click <a href="img">here</a> for an image</p>')
                elif self.path == '/img':
                    try:
                        self.send_response(200)
                        self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=--jpgboundary')
                        self.end_headers()
                        fpsCounter = 0
                        timeCounter = time.time()
                        while True:
                            jpegImage = node.io['jpeg'].get()
                            self.wfile.write("--jpgboundary".encode())
                            self.wfile.write(bytes([13, 10]))
                            self.send_header('Content-type', 'image/jpeg')
                            self.send_header('Content-length', str(len(jpegImage.getData())))
                            self.end_headers()
                            self.wfile.write(jpegImage.getData())
                            self.end_headers()
    
                            fpsCounter = fpsCounter + 1
                            if time.time() - timeCounter > 1:
                                node.warn(f'FPS: {fpsCounter}')
                                fpsCounter = 0
                                timeCounter = time.time()
                    except Exception as ex:
                        node.warn(str(ex))
    
        with ThreadingSimpleServer(("", PORT), HTTPHandler) as httpd:
            node.warn(f"Serving at {get_ip_address('re0')}:{PORT}")
            httpd.serve_forever()
    """)
    script.setScript(
        scrpt_str.safe_substitute(_PORT=port)
    )

    # Connections
    cam.video.link(jpeg.input)
    jpeg.bitstream.link(script.inputs['jpeg'])
    return pipeline


if __name__ == '__main__':
    # Connect to device with pipeline
    device_info = getDeviceInfo()
    with dai.Device(create_pipeline(port=5000, blob_path=None, config_path=None, host_ip=None), device_info) as device:
        click.echo(f"\t>>> Name: {device_info.name}")
        click.echo(f"\t>>> MXID: {device.getMxId()}")
        click.echo(f"\t>>> Cameras: {[c.name for c in device.getConnectedCameras()]}")
        click.echo(f"\t>>> USB speed: {device.getUsbSpeed().name}")
        while not device.isClosed():
            time.sleep(1)
