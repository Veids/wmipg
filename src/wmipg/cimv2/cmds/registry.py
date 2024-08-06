from binascii import unhexlify
import cmd2
import argparse

from impacket import system_errors

from wmipg.cimv2.lib.registry import Registry, RegValueTypeEnum


@cmd2.with_default_category("System")
class RegistryCMD(cmd2.CommandSet):
    registry: Registry

    def __init__(self, wmi_connector):
        super().__init__()
        self.registry = Registry(wmi_connector)

    reg_parser = cmd2.Cmd2ArgumentParser(description="StdRegProv operations")
    reg_subparsers = reg_parser.add_subparsers(title="entity", help="Command")

    @cmd2.with_argparser(reg_parser)
    def do_reg(self, ns: argparse.Namespace):
        handler = ns.cmd2_handler.get()
        if handler is not None:
            handler(ns)
        else:
            self.do_help("reg")

    reg_enum_parser = cmd2.Cmd2ArgumentParser(
        description="Enumerate juicy registry content (WinSCP)"
    )

    @cmd2.as_subcommand_to("reg", "enum", reg_enum_parser)
    def reg_enum(self, _):
        res = self.registry.enum()
        print(res)

    reg_query_parser = cmd2.Cmd2ArgumentParser(description="Query registry")
    reg_query_parser.add_argument("key_name", type=str)
    reg_query_parser.add_argument("-v", "--value", type=str, required=False)
    reg_query_parser.add_argument(
        "-t",
        "--type",
        type=RegValueTypeEnum.from_string,
        choices=list(RegValueTypeEnum),
        default=RegValueTypeEnum.string,
    )

    @cmd2.as_subcommand_to("reg", "query", reg_query_parser)
    def reg_query(self, ns: argparse.Namespace):
        print(self.registry.query(ns.key_name, ns.value, ns.type))

    reg_set_parser = cmd2.Cmd2ArgumentParser(description="Set registry key")
    reg_set_parser.add_argument("key_name", type=str)
    reg_set_parser.add_argument("-v", "--value", type=str, required=True)
    reg_set_parser.add_argument("-d", "--data", type=str, required=True)
    reg_set_parser.add_argument(
        "-t",
        "--type",
        type=RegValueTypeEnum,
        choices=list(RegValueTypeEnum),
        default=RegValueTypeEnum.string,
    )

    @cmd2.as_subcommand_to("reg", "set", reg_set_parser)
    def reg_set(self, ns: argparse.Namespace):
        if ns.type == RegValueTypeEnum.binary:
            ns.data = unhexlify(ns.data)

        res = self.registry.set_value(ns.key_name, ns.value, ns.data, ns.type)
        rv = res.ReturnValue
        msg = " - ".join(system_errors.ERROR_MESSAGES[rv])

        print(f"Result {rv}: {msg}")

    reg_delete_parser = cmd2.Cmd2ArgumentParser(description="Delete registry key")
    reg_delete_parser.add_argument("key_name", type=str)
    reg_delete_parser.add_argument("-v", "--value", type=str, required=True)

    @cmd2.as_subcommand_to("reg", "delete", reg_delete_parser)
    def reg_delete(self, ns: argparse.Namespace):
        res = self.registry.delete(ns.key_name, ns.value)
        rv = res.ReturnValue
        msg = " - ".join(system_errors.ERROR_MESSAGES[rv])

        print(f"Result {rv}: {msg}")
