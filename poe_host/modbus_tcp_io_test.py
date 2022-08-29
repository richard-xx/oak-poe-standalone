#!/usr/bin/env python3
# coding=utf-8

import argparse
import time

from loguru import logger
from pyModbusTCP.client import ModbusClient

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-H", "--host", type=str, default="169.254.1.222", help="Host")
parser.add_argument("-p", "--port", type=int, default=5000, help="TCP port")
args = parser.parse_args()


def cli():
    # init modbus client
    client = ModbusClient(host=args.host, port=args.port, auto_open=True, debug=False)
    bit = True
    ad = 0
    while True:
        logger.info("write holding registers")
        logger.info("----------")
        h_registers_is_ok = client.write_multiple_registers(ad, [bit] * 4)
        if h_registers_is_ok:
            logger.info("holding register #%s: write to %s" % (ad, bit))
        else:
            logger.error("holding register #%s: unable to write %s" % (ad, bit))

        time.sleep(2)

        logger.info("read holding registers")
        logger.info("---------")
        holding_registers = client.read_coils(0, 4)
        if holding_registers:
            logger.success("holding registers #0 to 3: %s" % holding_registers)
        else:
            logger.error("holding registers #0 to 3: unable to read")

        time.sleep(2)

        logger.info("write coils")
        logger.info("----------")
        coils_is_ok = client.write_multiple_coils(ad, [bit] * 4)
        if coils_is_ok:
            logger.success("coil #%s: write to %s" % (ad, bit))
        else:
            logger.error("coil #%s: unable to write %s" % (ad, bit))

        time.sleep(2)

        logger.info("read coils")
        logger.info("---------")
        coils = client.read_coils(0, 4)
        if coils:
            logger.success("coils #0 to 3: %s" % coils)
        else:
            logger.error("coils #0 to 3: unable to read")

        # toggle
        bit = not bit

        time.sleep(2)


if __name__ == "__main__":
    cli()
