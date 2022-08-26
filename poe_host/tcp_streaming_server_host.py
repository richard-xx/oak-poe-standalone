# coding=utf-8
import argparse
import socket

import cv2
import numpy as np

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


def cli():
    sock = socket.socket()
    sock.connect((args.host, args.port))

    try:
        while True:
            header = str(sock.recv(32), encoding="ascii")
            chunks = header.split()
            if chunks[0] == "ABCDE":
                # print(f">{header}<")
                ts = float(chunks[1])
                imgSize = int(chunks[2])
                img = get_frame(sock, imgSize)
                buf = np.frombuffer(img, dtype=np.byte)
                # print(buf.shape, buf.size)
                frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
                cv2.imshow("color", frame)
            if cv2.waitKey(1) == ord("q"):
                break
    except Exception as e:
        print("Error:", e)

    sock.close()


if __name__ == "__main__":
    cli()
