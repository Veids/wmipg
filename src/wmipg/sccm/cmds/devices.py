import cmd2
import argparse

from wmipg.common import print_data
from wmipg.sccm.lib import Devices


@cmd2.with_default_category("Devices")
class DevicesCMD(cmd2.CommandSet):
    devices: Devices

    def __init__(self, wmi_connector):
        super().__init__()
        self.devices = Devices(wmi_connector)

    get_device_parser = cmd2.Cmd2ArgumentParser()
    get_device_parser.add_argument(
        "-u",
        "--userName",
        action="store",
        type=str,
        default=None,
        help="LastLogonUserName",
    )
    get_device_parser.add_argument(
        "-nb",
        "--netbiosName",
        action="store",
        type=str,
        default=None,
        help="Device NetbiosName",
    )
    get_device_parser.add_argument(
        "-p",
        "--property",
        action="append",
        type=str,
        default=None,
        help="Property to output",
    )

    @cmd2.as_subcommand_to("get", "device", get_device_parser)
    def get_device(self, ns: argparse.Namespace):
        devices = self.devices.get(ns.userName, ns.netbiosName, ns.property)
        print_data(devices)

    get_primary_device_parser = cmd2.Cmd2ArgumentParser()
    get_primary_device_parser_group = (
        get_primary_device_parser.add_mutually_exclusive_group(required=True)
    )
    get_primary_device_parser_group.add_argument(
        "-u",
        "--userName",
        action="store",
        type=str,
        default=None,
        help="UniqueUserName",
    )
    get_primary_device_parser_group.add_argument(
        "-ri",
        "--resourceID",
        action="store",
        type=str,
        default=None,
        help="ID of the resource",
    )
    get_primary_device_parser_group.add_argument(
        "-rn",
        "--resourceName",
        action="store",
        type=str,
        default=None,
        help="Name of the resource",
    )

    @cmd2.as_subcommand_to("get", "primary-device", get_primary_device_parser)
    def get_primary_device(self, ns: argparse.Namespace):
        devices = self.devices.get_primary(ns.userName, ns.resourceID, ns.resourceName)
        print_data(devices)
