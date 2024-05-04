import cmd2
import argparse

from common import WMIConnector
from sccm.cmds import (
    ApplicationsCMD,
    CollectionsCMD,
    DeploymentsCMD,
    DevicesCMD,
    OperationsCMD,
    PoliciesCMD,
    RulesCMD,
    ScriptsCMD,
    SettingsCMD,
)


@cmd2.with_default_category("SCCM")
class SMS(cmd2.CommandSet):
    paths = ["root/sms/site_"]
    subcmds: list
    wmi: WMIConnector

    def __init__(self, connector: WMIConnector):
        super().__init__()
        self.wmi = connector
        self.subcmds = [
            ApplicationsCMD(connector),
            CollectionsCMD(connector),
            DeploymentsCMD(connector),
            DevicesCMD(connector),
            OperationsCMD(connector),
            PoliciesCMD(connector),
            RulesCMD(connector),
            ScriptsCMD(connector),
            SettingsCMD(connector),
        ]

    def check_namespace(self, namespace: str) -> bool:
        base = self.paths[0]
        return namespace.lower().startswith(base)

    def load_subcommands(self, cmd: cmd2.Cmd):
        for x in self.subcmds:
            cmd.register_command_set(x)

    def unload_subcommands(self, cmd: cmd2.Cmd):
        for x in self.subcmds:
            cmd.unregister_command_set(x)

    get_parser = cmd2.Cmd2ArgumentParser()
    get_subparsers = get_parser.add_subparsers(
        title="entity", help="information to query"
    )

    @cmd2.with_argparser(get_parser)
    def do_get(self, ns: argparse.Namespace):
        handler = ns.cmd2_handler.get()
        if handler is not None:
            # Call whatever subcommand function was selected
            handler(ns)
        else:
            # No subcommand was provided, so call help
            self.poutput("This command does nothing without sub-parsers registered")
            self.do_help("get")

    add_parser = cmd2.Cmd2ArgumentParser()
    add_subparsers = add_parser.add_subparsers(
        title="entity", help="information to add"
    )

    @cmd2.with_argparser(add_parser)
    def do_add(self, ns: argparse.Namespace):
        handler = ns.cmd2_handler.get()
        if handler is not None:
            # Call whatever subcommand function was selected
            handler(ns)
        else:
            # No subcommand was provided, so call help
            self.poutput("This command does nothing without sub-parsers registered")
            self.do_help("add")

    del_parser = cmd2.Cmd2ArgumentParser()
    del_subparsers = del_parser.add_subparsers(
        title="entity", help="information to delete"
    )

    @cmd2.with_argparser(del_parser)
    def do_del(self, ns: argparse.Namespace):
        handler = ns.cmd2_handler.get()
        if handler is not None:
            # Call whatever subcommand function was selected
            handler(ns)
        else:
            # No subcommand was provided, so call help
            self.poutput("This command does nothing without sub-parsers registered")
            self.do_help("del")

    update_parser = cmd2.Cmd2ArgumentParser()
    update_subparsers = update_parser.add_subparsers(
        title="entity", help="information to update"
    )

    @cmd2.with_argparser(update_parser)
    def do_update(self, ns: argparse.Namespace):
        handler = ns.cmd2_handler.get()
        if handler is not None:
            # Call whatever subcommand function was selected
            handler(ns)
        else:
            # No subcommand was provided, so call help
            self.poutput("This command does nothing without sub-parsers registered")
            self.do_help("update")
