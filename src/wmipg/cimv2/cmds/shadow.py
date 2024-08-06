import cmd2
import argparse

from wmipg.cimv2.lib.shadow import Shadow, ShadowStates
from wmipg.common import WMIConnector, print_data


@cmd2.with_default_category("System")
class ShadowCMD(cmd2.CommandSet):
    shadow: Shadow
    wmi: WMIConnector

    def __init__(self, wmi_connector):
        super().__init__()
        self.shadow = Shadow(wmi_connector)
        self.wmi = wmi_connector

    shadow_parser = cmd2.Cmd2ArgumentParser(description="Interact with shadow copies")
    shadow_subparsers = shadow_parser.add_subparsers(
        title="action", help="shadow operation"
    )

    @cmd2.with_argparser(shadow_parser)
    def do_shadow(self, ns: argparse.Namespace):
        handler = ns.cmd2_handler.get()
        if handler is not None:
            handler(ns)
        else:
            self._cmd.do_help("shadow")

    shadow_list_parser = cmd2.Cmd2ArgumentParser(description="Enumerate shadow copies")

    @cmd2.as_subcommand_to("shadow", "list", shadow_list_parser)
    def shadow_list(self, _):
        def shadowListFormatter(prop, _):
            value = prop["value"]
            if prop["name"] == "State":
                name = ShadowStates(value).name
                return f"{name} ({value})"

            return value

        print_data(
            self.shadow.list(),
            customFormatter=shadowListFormatter,
        )

    shadow_create_parser = cmd2.Cmd2ArgumentParser(description="Create a shadow copy")
    shadow_create_parser.add_argument(
        "volume", action="store", type=str, help="Target volume"
    )

    @cmd2.as_subcommand_to("shadow", "create", shadow_create_parser)
    def shadow_create(self, ns: argparse.Namespace):
        res = self.shadow.create(ns.volume)
        print(f"Created {res.ShadowID}")

    shadow_delete_parser = cmd2.Cmd2ArgumentParser(description="Remove a shadow copy")
    shadow_delete_parser.add_argument(
        "ID", action="store", type=str, help="Target ShadowID"
    )

    @cmd2.as_subcommand_to("shadow", "delete", shadow_delete_parser)
    def shadow_delete(self, ns: argparse.Namespace):
        self.wmi.checkiWbemResponse(
            f"Removing shadow {ns.ID}",
            self.shadow.delete(ns.ID),
        )
