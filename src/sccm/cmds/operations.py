import cmd2
import argparse

from common import print_data
from sccm.lib import Operations


@cmd2.with_default_category("Operations")
class OperationsCMD(cmd2.CommandSet):
    operations: Operations

    def __init__(self, wmi_connector):
        super().__init__()
        self.operations = Operations(wmi_connector)

    get_operation_status_parser = cmd2.Cmd2ArgumentParser()
    get_operation_status_parser.add_argument(
        "-oi",
        "--operationID",
        action="store",
        type=int,
        default=None,
        help="ID of the operation",
    )
    get_operation_status_parser.add_argument(
        "-p",
        "--property",
        action="append",
        type=str,
        default=None,
        help="Property to output",
    )

    @cmd2.as_subcommand_to("get", "operation-status", get_operation_status_parser)
    def get_operation_status(self, ns: argparse.Namespace):
        print_data(self.operations.get_status(ns.operationID, ns.property))

    del_operation_parser = cmd2.Cmd2ArgumentParser()
    del_operation_parser.add_argument(
        "-oi",
        "--operationID",
        action="store",
        type=int,
        required=True,
        help="ID of the operation",
    )

    @cmd2.as_subcommand_to("del", "operation", del_operation_parser)
    def del_operation(self, ns: argparse.Namespace):
        self.operations.remove(ns.operationID)
