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


def send_lens_pos(socket, value):
    # Leave 28 bytes for other data user might want to send to the device, eg. exposure/iso setting
    header = f"{str(value).ljust(3)},{''.ljust(28)}"  # 32 bytes in total.
    print(f"Setting manual focus to", value)
    socket.send(bytes(header, encoding="ascii"))


def cli():
    sock = socket.socket()
    sock.connect((args.host, args.port))

    lensPos = 100

    try:
        while True:
            header = sock.recv(32).decode("ascii")
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

            key = cv2.waitKey(1)
            if key == ord("q"):
                break
            elif key == ord(".") and lensPos < 255:  # lensPos ++
                lensPos += 1
                send_lens_pos(sock, lensPos)
            elif key == ord(",") and 0 < lensPos:  # lensPos --
                lensPos -= 1
                send_lens_pos(sock, lensPos)

    except Exception as e:
        print("Error:", e)

    sock.close()


if __name__ == "__main__":
    cli()
