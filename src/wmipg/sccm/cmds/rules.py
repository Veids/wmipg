import cmd2
import argparse

from wmipg.sccm.lib import Rules
from wmipg.common import print_data


@cmd2.with_default_category("Rules")
class RulesCMD(cmd2.CommandSet):
    rules: Rules

    def __init__(self, wmi_connector):
        super().__init__()
        self.rules = Rules(wmi_connector)

    get_rule_parser = cmd2.Cmd2ArgumentParser()
    get_rule_parser.add_argument(
        "-i", "--ruleID", action="store", type=str, required=True
    )

    @cmd2.as_subcommand_to("get", "rule", get_rule_parser)
    def get_rule(self, ns: argparse.Namespace):
        rules = self.rules.get(ns.ruleID)
        print_data(rules)
