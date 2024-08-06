import cmd2
import argparse

from wmipg.common import WMIConnector, print_data
from wmipg.cimv2.lib.share import Share, ShareTypeEnum


@cmd2.with_default_category("System")
class ShareCMD(cmd2.CommandSet):
    share: Share
    wmi: WMIConnector

    def __init__(self, wmi_connector):
        super().__init__()
        self.share = Share(wmi_connector)
        self.wmi = wmi_connector

    share_parser = cmd2.Cmd2ArgumentParser(description="Interact with Windows shares")
    share_subparsers = share_parser.add_subparsers(
        title="action", help="Windows shares operations"
    )

    @cmd2.with_argparser(share_parser)
    def do_share(self, ns: argparse.Namespace):
        handler = ns.cmd2_handler.get()
        if handler is not None:
            handler(ns)
        else:
            self._cmd.do_help("share")

    share_list_parser = cmd2.Cmd2ArgumentParser(description="Enumerate shares")

    @cmd2.as_subcommand_to("share", "list", share_list_parser)
    def share_list(self, _):
        """List windows shares"""

        print_data(self.share.list())

    share_create_parser = cmd2.Cmd2ArgumentParser(description="Create a share")
    share_create_parser.add_argument(
        "path", action="store", type=str, help="Path (e.g C:\\)"
    )
    share_create_parser.add_argument(
        "name", action="store", type=str, help="Name of the share (e.g C$, myshare)"
    )
    share_create_parser.add_argument(
        "type",
        type=ShareTypeEnum.from_string,
        choices=list(ShareTypeEnum),
        default=ShareTypeEnum.DISK_DRIVE,
    )
    share_create_parser.add_argument(
        "--desc",
        "--description",
        action="store",
        type=str,
        default="",
        help="Share description",
    )
    share_create_parser.add_argument(
        "--password", action="store", type=str, default="", help="Share password"
    )

    @cmd2.as_subcommand_to("share", "create", share_create_parser)
    def share_create(self, ns: argparse.Namespace):
        r = self.share.create(ns.path, ns.name, ns.type.value, ns.desc, ns.password)
        print(r.name)

    share_delete_parser = cmd2.Cmd2ArgumentParser(description="Delete a share")
    share_delete_parser.add_argument(
        "name", action="store", type=str, help="Name (e.g C$)"
    )

    @cmd2.as_subcommand_to("share", "delete", share_delete_parser)
    def share_delete(self, ns: argparse.Namespace):
        self.wmi.checkiWbemResponse(
            f"Removing share {ns.name}",
            self.share.delete(ns.name),
        )

    share_get_access_mask_parser = cmd2.Cmd2ArgumentParser(
        description="Get access mask"
    )
    share_get_access_mask_parser.add_argument(
        "share", action="store", type=str, help="Share (e.g C$)"
    )

    @cmd2.as_subcommand_to("share", "get_access_mask", share_get_access_mask_parser)
    def share_get_mask(self, ns: argparse.Namespace):
        amf = self.share.get_access_mask(ns.share)
        print(f"{amf.value}: {amf.name}")
