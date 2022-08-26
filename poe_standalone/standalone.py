# coding=utf-8
import socket
import time
from functools import partial
from ipaddress import IPv4Address
from pathlib import Path
from urllib import request
from urllib.error import URLError

import depthai as dai
import numpy as np
# import click
import rich_click as click
from click_params import IPV4_ADDRESS, IP_ADDRESS
from validators import ip_address
try:
    from poe_standalone import script_http_server, script_mjpeg_server
    from poe_standalone.tcp_streaming_client import tcp_streaming_client
    from poe_standalone.tcp_streaming_server import (
        tcp_streaming_server,
        tcp_streaming_server_config_focus,
    )
    from poe_standalone.utils import getDeviceInfo, get_local_ip, lazy_import
    from poe_standalone.yolo import yolo_decoding, yolo_stereo_decoding
except ImportError:
    import script_http_server, script_mjpeg_server
    from tcp_streaming_client import tcp_streaming_client
    from tcp_streaming_server import (
        tcp_streaming_server,
        tcp_streaming_server_config_focus,
    )
    from utils import getDeviceInfo, get_local_ip, lazy_import
    from yolo import yolo_decoding, yolo_stereo_decoding

create_pipelines = {
    "script_http_server": script_http_server.create_pipeline,
    "script_mjpeg_server": script_mjpeg_server.create_pipeline,
    "tcp_streaming_server": tcp_streaming_server.create_pipeline,
    "tcp_streaming_server_config_focus": tcp_streaming_server_config_focus.create_pipeline,
    "tcp_streaming_client": tcp_streaming_client.create_pipeline,
    "yolo_decoding": yolo_decoding.create_pipeline,
    "yolo_stereo_decoding": yolo_stereo_decoding.create_pipeline,
    "custom_pipeline": "",
}

click.option = partial(click.option, show_default=True)

deviceInfos = [device_info for device_info in dai.Device.getAllAvailableDevices() if ip_address.ipv4(device_info.name)]
deviceInfos.sort(key=lambda device_info: int(IPv4Address(device_info.name)))
deviceIps = {deviceInfo.name: deviceInfo.getMxId() for deviceInfo in deviceInfos}

deviceInfos = {deviceInfo.getMxId(): deviceInfo for deviceInfo in deviceInfos}



@click.group(
    context_settings=dict(
        help_option_names=["-h", "--help"],
        # token_normalize_func=lambda x: x.lower(),
    ),
    invoke_without_command=True,
    help="OAK POE STANDALONE SCRIPTS",
)
@click.option(
    "-device_ip",
    "--device_ip",
    prompt=True,
    prompt_required=False,
    type=click.Choice(choices=deviceIps, case_sensitive=False),
    default=None,
    help="The IP of the OAK device you want to connect to. The default is to list all for you to choose from.",
)
@click.option(
    "-host_ip",
    "--host_ip",
    prompt=True,
    prompt_required=False,
    # type=click.STRING,
    default=get_local_ip(),
    help="The IP of the Host pc you want to connect to.",
)
@click.option(
    "-P",
    "--pipeline",
    prompt=True,
    prompt_required=False,
    type=click.Choice(choices=create_pipelines, case_sensitive=False),
    default="script_http_server",
    help="Pipeline you want to start. ",
)
@click.option(
    "-cp",
    "--custom_pipeline",
    prompt="Custom pipeline path",
    prompt_required=False,
    default=None,
    type=click.Path(exists=True, path_type=Path),
    help="The custom pipeline you want to start.",
)
@click.option(
    "-p",
    "--port",
    prompt="NETWORK PORT",
    prompt_required=False,
    type=click.INT,
    default=5000,
    help="NETWORK PORT",
)
@click.option(
    "-b",
    "--blob_path",
    prompt="YOLO Blob path to use",
    prompt_required=False,
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="YOLO Blob path to use",
)
@click.option(
    "-c",
    "--config_path",
    prompt="YOLO Config path to use",
    prompt_required=False,
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="YOLO Config path to use",
)
@click.pass_context
def cli(ctx, device_ip, host_ip, pipeline, custom_pipeline, port, blob_path, config_path):
    click.echo(click.get_current_context().params)
    ctx.ensure_object(dict)
    ctx.obj["device_id"] = deviceIps.get(device_ip)
    if "yolo" in pipeline:
        if blob_path is None:
            blob_path = click.prompt(
                "Prompt the yolo blob path",
                type=click.Path(exists=True, path_type=Path),
            )
        if config_path is None:
            config_path = click.prompt(
                "Prompt the yolo config json path",
                type=click.Path(exists=True, path_type=Path),
            )
    ctx.obj["port"] = port
    ctx.obj["blob_path"] = blob_path
    ctx.obj["config_path"] = config_path
    if pipeline == "custom_pipeline":
        custom_pipeline = lazy_import("create_pipeline", custom_pipeline)
        ctx.obj["create_pipeline"] = custom_pipeline.create_pipeline(
            port, blob_path, config_path, host_ip
        )
    else:
        ctx.obj["create_pipeline"] = create_pipelines.get(pipeline)(
            port, blob_path, config_path, host_ip
        )
    if ctx.invoked_subcommand is None:
        ctx.invoke(host_run)


blTypes = {
    "auto": dai.DeviceBootloader.Type.AUTO,
    "usb": dai.DeviceBootloader.Type.USB,
    "net": dai.DeviceBootloader.Type.NETWORK,
}


@cli.command(
    "flash_bootloader",
    short_help="Flash the bootloader to the device",
    help="This script will flash bootloader to the connected OAK camera. "
         "Bootloader can only be flashed to devices that have flash on-board.",
)
@click.argument("bl_type", type=click.Choice(blTypes), default="auto")
@click.pass_context
def flash_bootloader(ctx, bl_type):
    blType = blTypes.get(bl_type)
    if ctx.obj["device_id"]:
        device_info = deviceInfos[ctx.obj["device_id"]]
    else:
        device_info = getDeviceInfo()

    hasBootloader = device_info.state == dai.XLinkDeviceState.X_LINK_BOOTLOADER
    if hasBootloader:
        if not click.confirm(
                "Warning! Flashing bootloader can potentially soft brick your device and should be done with caution.\n"
                "Do not unplug your device while the bootloader is flashing.\n"
                "Type 'y' and press enter to proceed, otherwise exits: "
        ):
            click.echo("Prompt declined, exiting...")
            exit(-1)

    # Open DeviceBootloader and allow flashing bootloader
    click.echo(f"Booting latest bootloader first, will take a tad longer...")
    with dai.DeviceBootloader(device_info, allowFlashingBootloader=True) as bl:
        click.echo(f"Bootloader version to flash: {bl.getVersion()}")
        currentBlType = bl.getType()

        if blType == dai.DeviceBootloader.Type.AUTO:
            blType = currentBlType

        # Check if bootloader type is the same, if already booted by bootloader (not in USB recovery mode)
        if currentBlType != blType and hasBootloader:
            if not click.confirm(
                    f"Are you sure you want to flash {blType.name} bootloader over current {currentBlType.name} bootloader?\n"
                    f"Type 'y' and press enter to proceed, otherwise exits: "
            ):
                print("Prompt declined, exiting...")
                exit(-1)

        # Create a progress callback lambda
        progress = lambda p: click.echo(f"\rFlashing progress: {p:.2%}", nl=False)

        # bar = click.progressbar(length=10, label="Flashing progress: ",)
        # progress = lambda p: bar.update(p)

        # click.echo(f"Flashing {blType.name} bootloader...")
        startTime = time.monotonic()
        (res, message) = bl.flashBootloader(
            dai.DeviceBootloader.Memory.FLASH, blType, progress
        )
        click.echo()
        if res:
            click.echo(
                f"Flashing successful. Took {time.monotonic() - startTime} seconds"
            )
        else:
            click.echo(
                f"Flashing failed:{message}",
            )


@cli.command(
    "clear_pipeline",
    short_help="Clear the flashed app on the device",
    help="Clear the flashed app on the device by removing the SBR boot structure "
         "without removing the fast boot header feature to still boot the app",
)
@click.pass_context
def clear_pipeline(ctx):
    if ctx.obj["device_id"]:
        device_info = deviceInfos[ctx.obj["device_id"]]
    else:
        device_info = getDeviceInfo()
    bootloader = dai.DeviceBootloader(device_info)
    click.echo(f"{bootloader.flashClear()}")


@cli.command(
    "run",
    short_help="Run the program in host mode",
)
@click.pass_context
def host_run(ctx):
    # Connect to device with pipeline
    if ctx.obj["device_id"]:
        device_info = deviceInfos[ctx.obj["device_id"]]
    else:
        device_info = getDeviceInfo()
    with dai.Device(ctx.obj["create_pipeline"], device_info) as device:
        eeprom_data = device.readCalibration2().getEepromData()
        click.echo(f"\t>>> Name: {device_info.name}")
        click.echo(f"\t>>> MXID: {device.getMxId()}")
        click.echo(f"\t>>> Cameras: {[c.name for c in device.getConnectedCameras()]}")
        click.echo(f"\t>>> USB speed: {device.getUsbSpeed().name}")
        click.echo(f"\t>>> Board name: {eeprom_data.boardName}")
        click.echo(f"\t>>> Product name: {eeprom_data.productName}")
        try:
            request.urlopen(f"http://{device_info.name}:{ctx.obj['port']}")
            click.launch(f"http://{device_info.name}:{ctx.obj['port']}")
        except URLError:
            pass
        click.echo(f"you can try access http://{device_info.name}:{ctx.obj['port']}")
        while not device.isClosed():
            time.sleep(1)


@cli.command(
    "flash_pipeline",
    short_help="Flash the pipeline to the device",
    help="This script will flash pipeline to the connected OAK camera, along with its assests (eg. AI models). ",
)
@click.option(
    "-d",
    "--dap",
    prompt_required=False,
    prompt="Depthai Application Package Path",
    default="",
    type=click.Path(),
    help="Depthai Application Package Path",
)
@click.pass_context
def flash_pipeline(ctx, dap):
    if ctx.obj["device_id"]:
        device_info = deviceInfos[ctx.obj["device_id"]]
    else:
        device_info = getDeviceInfo()
    bootloader = dai.DeviceBootloader(device_info)
    # bar = click.progressbar(length=10, label="Flashing progress: ")
    # progress = lambda p: bar.update(p)

    progress = lambda p: click.echo(f"\rFlashing progress: {p:.2%}", nl=False)

    if dap:
        bootloader.flashDepthaiApplicationPackage(
            progress, np.fromfile(dap, dtype="uint8")
        )
    else:
        bootloader.flash(progress, ctx.obj["create_pipeline"], compress=True)
    click.echo()


@cli.command(
    "save_pipeline",
    short_help="Saves application package to a file which can be flashed to depthai device.",
    help="Saves application package to a file which can be flashed to depthai device.",
)
@click.argument("dap_name", default=f"pipeline_{time.strftime('%Y%m%d_%H%M')}.dap")
@click.pass_context
def save_pipeline(ctx, dap_name):
    if ctx.obj["device_id"]:
        device_info = deviceInfos[ctx.obj["device_id"]]
    else:
        device_info = getDeviceInfo()
    bootloader = dai.DeviceBootloader(device_info)
    bootloader.saveDepthaiApplicationPackage(
        dap_name, ctx.obj["create_pipeline"], compress=True
    )


@cli.command(
    "set_ip",
    short_help="Sets IP of the POE device",
    help="This script allows you to set static or dynamic IP, or clear bootloader config on your OAK-POE device. \t"
         "Make sure to set mask and gateway correctly! If they are set incorrectly you will soft-brick your device ("
         "you won’t be able to access it), and will have to factory reset your OAK PoE. "
)
@click.pass_context
def set_ip(ctx):
    if ctx.obj["device_id"]:
        device_info = deviceInfos[ctx.obj["device_id"]]
    else:
        device_info = getDeviceInfo()
    click.echo(f"Found device with name: {device_info.name}")
    click.echo("-------------------------------------")
    click.echo('"1" to set a static IPv4 address')
    click.echo('"2" to set a dynamic IPv4 address')
    click.echo('"3" to clear the config')
    key = click.prompt("Enter the number", type=click.IntRange(1, 3))
    click.echo("-------------------------------------")
    with dai.DeviceBootloader(device_info) as bl:
        if key in [1, 2]:
            ipv4 = click.prompt("Enter IPv4", type=IPV4_ADDRESS)
            mask = click.prompt("Enter IPv4 Mask", type=IPV4_ADDRESS)
            gateway = click.prompt("Enter IPv4 Gateway", type=IPV4_ADDRESS)
            mode = "static" if key == 1 else "dynamic"
            if not click.confirm(
                    f"Flashing {mode} IPv4 {ipv4}, mask {mask}, gateway {gateway} "
                    f"to the POE device. Enter 'y' to confirm. "
            ):
                raise Exception("Flashing aborted.")

            conf = dai.DeviceBootloader.Config()
            if key == 1:
                conf.setStaticIPv4(ipv4, mask, gateway)
            elif key == 2:
                conf.setDynamicIPv4(ipv4, mask, gateway)
            (success, error) = bl.flashConfig(conf)
        elif key == 3:
            (success, error) = bl.flashConfigClear()

        if not success:
            click.echo(f"Flashing failed: {error}")
        else:
            click.echo(f"Flashing successful.")


if __name__ == "__main__":
    cli(obj={})
