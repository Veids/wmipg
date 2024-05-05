import cmd2
import argparse

from wmipg.sccm.lib import Policies


@cmd2.with_default_category("Policies")
class PoliciesCMD(cmd2.CommandSet):
    policies: Policies

    def __init__(self, wmi_connector):
        super().__init__()
        self.policies = Policies(wmi_connector)

    update_machine_policy_parser = cmd2.Cmd2ArgumentParser()
    update_machine_policy_parser.add_argument(
        "-ci",
        "--collectionID",
        action="store",
        type=str,
        required=True,
        help="ID of the collection",
    )
    update_machine_policy_parser.add_argument(
        "-ri",
        "--resourceID",
        action="append",
        type=int,
        required=True,
        help="ID of the resource",
    )

    @cmd2.as_subcommand_to("update", "machine-policy", update_machine_policy_parser)
    def update_machine_policy(self, ns: argparse.Namespace):
        self.policies.update_machine(ns.collectionID, ns.resourceID)
