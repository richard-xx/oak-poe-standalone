# coding=utf-8
import argparse
import json
import socket
from collections import deque

import cv2
import numpy as np
try:
    from poe_host.yolo_utils import FPSHandler, drawRect, drawText, frameNorm
except ImportError:
    from yolo_utils import FPSHandler, drawRect, drawText, frameNorm

try:
    from turbojpeg import TurboJPEG, TJFLAG_FASTUPSAMPLE, TJFLAG_FASTDCT, TJPF_GRAY

    turbo = TurboJPEG()
except:
    turbo = None

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-H", "--host", type=str, default="169.254.1.222", help="Host")
parser.add_argument("-p", "--port", type=int, default=5000, help="TCP port")
args = parser.parse_args()


def get_frame(socket, size):
    bytes = socket.recv(4096)
    while True:
        read = 4096
        if size - len(bytes) < read:
            read = size - len(bytes)
        bytes += socket.recv(read)
        if size == len(bytes):
            return bytes


dets_queue = deque()


def cli():
    sock = socket.socket()
    sock.connect((args.host, args.port))

    fps = FPSHandler()
    while True:
        header = str(sock.recv(32), encoding="ascii")
        chunks = header.split()
        if chunks[0] == "DETECT":
            fps.tick("nn")
            # print(f">{header}<")
            ts = float(chunks[1])
            imgSize = int(chunks[2])
            data = sock.recv(imgSize)
            # print(f"{data = }")
            dets_queue.append(json.loads(data))
            # print(f"{dets_queue[-1] = }")
        elif chunks[0] == "FRAME":
            fps.tick("FRAME")
            # print(f">{header}<")
            ts = float(chunks[1])
            imgSize = int(chunks[2])
            img = get_frame(sock, imgSize)
            buf = np.frombuffer(img, dtype=np.byte)
            # print(buf.shape, buf.size)
            frame = (
                turbo.decode(data, flags=TJFLAG_FASTUPSAMPLE | TJFLAG_FASTDCT)
                if turbo
                else cv2.imdecode(buf, cv2.IMREAD_COLOR)
            )

            if dets_queue:
                detections = dets_queue.popleft()
                for detection in detections:
                    bbox = frameNorm(
                        frame,
                        (
                            detection["xmin"],
                            detection["ymin"],
                            detection["xmax"],
                            detection["ymax"],
                        ),
                    )
                    drawRect(
                        frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), "red", "red", 1
                    )
                    drawText(
                        frame,
                        f'{detection["label"]}: {detection["confidence"]:.2%}',
                        (bbox[0] + 5, bbox[1] - 10),
                    )
                    if detection.get("x"):
                        drawText(
                            frame,
                            f"X: {int(detection['x'])} mm",
                            (bbox[0] + 10, bbox[1] + 60),
                        )
                        drawText(
                            frame,
                            f"Y: {int(detection['y'])} mm",
                            (bbox[0] + 10, bbox[1] + 75),
                        )
                        drawText(
                            frame,
                            f"Z: {int(detection['z'])} mm",
                            (bbox[0] + 10, bbox[1] + 90),
                        )
            fps.drawFps(frame, "FRAME")
            cv2.imshow("color", frame)
        if cv2.waitKey(1) == ord("q"):
            break

    sock.close()


if __name__ == "__main__":
    cli()
