import cmd2
import argparse

from wmipg.common import print_data
from wmipg.cimv2.lib.generic import Generic, PingStatusCode


@cmd2.with_default_category("System")
class GenericCMD(cmd2.CommandSet):
    generic: Generic

    def __init__(self, wmi_connector):
        super().__init__()
        self.generic = Generic(wmi_connector)

    def do_env(self, _):
        """Print environment variables"""

        print_data(self.generic.env())

    ping_parser = cmd2.Cmd2ArgumentParser(
        description="Get ping result of a remote system"
    )
    ping_parser.add_argument(
        "address", action="store", type=str, help="Address to ping"
    )

    @cmd2.with_argparser(ping_parser)
    def do_ping(self, ns: argparse.Namespace):
        def pingFormatter(prop, _):
            value = prop["value"]
            if prop["name"] == "StatusCode":
                name = PingStatusCode(value).name.replace("_", " ")
                return f"{name} ({value})"

            return value

        print_data(
            self.generic.ping(ns.address),
            customFormatter=pingFormatter,
        )
