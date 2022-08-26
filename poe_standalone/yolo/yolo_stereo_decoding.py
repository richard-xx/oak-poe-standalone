# coding=utf-8
import json
import time

import click
import depthai as dai

try:
    from poe_standalone.utils import getDeviceInfo
except ImportError:
    from utils import getDeviceInfo

from string import Template

def readConfig(path) -> dict:
    """
    > Reads a JSON file and returns a dictionary of the contents

    copy from https://github.com/luxonis/depthai/blob/3b300202ba1a59ff1c3227af5bc0ba9b4cf994b4/depthai_sdk/src/depthai_sdk/managers/nnet_manager.py#L64


    :param path: The path to the model config file (.json)
    :return: The nn_config of the model.
    """

    configPath = Path(path)
    if not configPath.exists():
        raise ValueError("Path {} does not exist!".format(path))

    with configPath.open() as f:
        config = json.load(f)
        nnConfig = config.get("nn_config", {})
        metadata = nnConfig.get("NN_specific_metadata", {})

        labels = config.get("mappings", {}).get("labels", None)
        if labels:
            metadata["labels"] = labels
        if "input_size" in nnConfig:
            inputSize = tuple(map(int, nnConfig.get("input_size").split("x")))
            metadata["inputSize"] = inputSize

        confidence = metadata.get(
            "confidence_threshold", nnConfig.get("confidence_threshold", None)
        )
        metadata["confidence_threshold"] = confidence

    return metadata


def create_pipeline(port=5000, blob_path=None, config_path=None, host_ip=None):
    """
    It creates a pipeline that takes a video stream from the camera, runs it through the neural network, and then sends the
    video stream and the neural network output to a script node. The script node then sends the video stream and the neural
    network output to a TCP server

    :param blob_path: The path to the blob file
    :param config_path: Path to the configuration file
    :return: A pipeline object
    """

    nn_config = readConfig(config_path)
    # Start defining a pipeline
    pipeline = dai.Pipeline()

    camRgb = pipeline.createColorCamera()
    camRgb.setIspScale(2, 3)
    camRgb.setPreviewSize(camRgb.getIspSize())
    camRgb.setInterleaved(False)

    nn = pipeline.create(dai.node.YoloSpatialDetectionNetwork)
    nn.setBlobPath(blob_path)
    nn.setConfidenceThreshold(nn_config["confidence_threshold"])
    nn.setNumClasses(nn_config["classes"])
    nn.setCoordinateSize(nn_config["coordinates"])
    nn.setAnchors(nn_config["anchors"])
    nn.setAnchorMasks(nn_config["anchor_masks"])
    nn.setIouThreshold(nn_config["iou_threshold"])

    monoLeft = pipeline.create(dai.node.MonoCamera)
    monoLeft.setBoardSocket(dai.CameraBoardSocket.LEFT)

    monoLeft.setResolution(dai.MonoCameraProperties.SensorResolution.THE_720_P)

    monoRight = pipeline.create(dai.node.MonoCamera)
    monoRight.setBoardSocket(dai.CameraBoardSocket.RIGHT)
    monoRight.setResolution(dai.MonoCameraProperties.SensorResolution.THE_720_P)

    stereo = pipeline.createStereoDepth()

    stereo.initialConfig.setConfidenceThreshold(245)
    stereo.initialConfig.setMedianFilter(dai.MedianFilter.KERNEL_5x5)
    stereo.setLeftRightCheck(True)
    # stereo.setExtendedDisparity(extended)
    # stereo.setSubpixel(subpixel)
    stereo.setDepthAlign(dai.CameraBoardSocket.RGB)
    stereo.setOutputSize(*camRgb.getPreviewSize())

    monoLeft.out.link(stereo.left)
    monoRight.out.link(stereo.right)

    stereo.depth.link(nn.inputDepth)
    nn.setDepthLowerThreshold(100)
    nn.setDepthUpperThreshold(10000)
    nn.setBoundingBoxScaleFactor(0.5)

    manipNn = pipeline.create(dai.node.ImageManip)
    manipNn.initialConfig.setResize(*nn_config["inputSize"])
    manipNn.setMaxOutputFrameSize(
        nn_config["inputSize"][0] * nn_config["inputSize"][1] * 3
    )
    manipNn.out.link(nn.input)
    camRgb.preview.link(manipNn.inputImage)

    videoEnc = pipeline.create(dai.node.VideoEncoder)
    videoEnc.setDefaultProfilePreset(
        camRgb.getFps(), dai.VideoEncoderProperties.Profile.MJPEG
    )
    camRgb.video.link(videoEnc.input)

    script = pipeline.create(dai.node.Script)
    script.setProcessor(dai.ProcessorType.LEON_CSS)

    videoEnc.bitstream.link(script.inputs["frame"])
    script.inputs["frame"].setBlocking(False)
    script.inputs["frame"].setQueueSize(1)

    nn.out.link(script.inputs["detection"])
    script.inputs["detection"].setBlocking(False)
    script.inputs["detection"].setQueueSize(1)

    script_str = Template(
        """# coding=utf-8
        import fcntl
        import json
        import socket
        import struct
        from socketserver import StreamRequestHandler, ThreadingTCPServer
        
        
        def get_ip_address(ifname):
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            return socket.inet_ntoa(fcntl.ioctl(
                s.fileno(),
                -1071617759,  # SIOCGIFADDR
                struct.pack('256s', ifname[:15].encode())
            )[20:24])
        
        
        labelMap = ${_labelMap}
        PORT = ${_PORT}
        
        
        class DataHandler(StreamRequestHandler):
            def handle(self):
                node.warn(f'Got connection from {self.client_address}')
        
                while True:
                    bboxes = []
                    dets = node.io["detection"].get()
                    ts = dets.getTimestamp()
                    detections = dets.detections
                    for detection in detections:
                        bbox = {"label": labelMap[detection.label] if labelMap else detection.label,
                                "confidence": detection.confidence,
                                "xmin": detection.xmin,
                                "ymin": detection.ymin,
                                "xmax": detection.xmax,
                                "ymax": detection.ymax,
                                "x": detection.spatialCoordinates.x,
                                "y": detection.spatialCoordinates.y,
                                "z": detection.spatialCoordinates.z,
                                }
                        bboxes.append(bbox)
        
                    if bboxes:
                        bbox_str = json.dumps(bboxes)
                        header = f"DETECT" + str(ts.total_seconds()).center(18) + str(len(bbox_str)).center(8)
                        self.wfile.write(bytes(header, encoding='ascii'))
                        self.wfile.write(bytes(bbox_str, encoding='ascii'))
        
                    pck = node.io["frame"].get()
                    data = pck.getData()
                    ts = pck.getTimestamp()
                    header = f"FRAME " + str(ts.total_seconds()).center(18) + str(len(data)).center(8)
                    # node.warn(f'>{header}<')
                    self.wfile.write(bytes(header, encoding='ascii'))
                    self.wfile.write(data)
        
        
        with ThreadingTCPServer(('', PORT), DataHandler) as DataTCPServer:
            node.warn(f"DataTCPServer at {get_ip_address('re0')}:{PORT}")
            DataTCPServer.serve_forever()

        """
    )

    script.setScript(script_str.safe_substitute(_PORT=port, _labelMap=nn_config.get("labels")))
    return pipeline


if __name__ == "__main__":
    from pathlib import Path

    blobPath = Path(__file__).parent / "models/yolov5_640_openvino_2021.4_6shave.blob"
    configPath = Path(__file__).parent / "models/yolov5_640.json"
    # Connect to device with pipeline
    device_info = getDeviceInfo()
    with dai.Device(create_pipeline(blobPath, configPath), device_info) as device:
        click.echo(f">>> Name: {device_info.name}")
        click.echo(f">>> MXID: {device.getMxId()}")
        click.echo(f">>> Cameras: {[c.name for c in device.getConnectedCameras()]}")
        click.echo(f">>> USB speed: {device.getUsbSpeed().name}")
        with open("ip.txt", "w") as f:
            f.write(device_info.name)

        while not device.isClosed():
            time.sleep(1)
