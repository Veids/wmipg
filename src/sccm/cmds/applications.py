import cmd2
import argparse

from sccm.lib import Applications
from common import print_data, console


@cmd2.with_default_category("Applications")
class ApplicationsCMD(cmd2.CommandSet):
    applications: Applications

    def __init__(self, wmi_connector):
        super().__init__()
        self.applications = Applications(wmi_connector)

    add_application_parser = cmd2.Cmd2ArgumentParser()
    add_application_parser.add_argument(
        "-s", "--siteCode", action="store", type=str, required=True
    )
    add_application_parser.add_argument(
        "-an",
        "--applicationName",
        action="store",
        type=str,
        required=True,
        help="Name of the application",
    )
    add_application_parser.add_argument(
        "-p",
        "--path",
        action="store",
        type=str,
        required=True,
        help="Executable pass or command string with arguments",
    )
    add_application_parser.add_argument(
        "-r",
        "--runUser",
        action="store",
        type=str,
        required=True,
        choices=["User", "System"],
        help="Run command on behalf of the user/system",
    )
    add_application_parser.add_argument(
        "--show",
        action="store",
        type=bool,
        default=False,
        help="Don't hide an application from CCM console",
    )

    @cmd2.as_subcommand_to("add", "application", add_application_parser)
    def add_application(self, ns: argparse.Namespace):
        self.applications.add(
            ns.siteCode, ns.applicationName, ns.path, ns.runUser, ns.show
        )

    get_application_parser = cmd2.Cmd2ArgumentParser()
    get_application_parser.add_argument(
        "-n",
        "--applicationName",
        action="store",
        type=str,
        default=None,
        help="LocalizedDisplayName",
    )
    get_application_parser.add_argument(
        "-p",
        "--property",
        action="append",
        type=str,
        default=None,
        help="Property to output",
    )

    @cmd2.as_subcommand_to("get", "application", get_application_parser)
    def get_application(self, ns: argparse.Namespace):
        def columnFormatter(prop, obj):
            value = prop["value"]

            if prop["name"] == "ExecutionContext":
                return f"{value} (User)" if value else f"{value} (System)"

            return value

        applications = self.applications.get(ns.applicationName, ns.property)
        print_data(applications, columnFormatter)

    get_application_xml_parser = cmd2.Cmd2ArgumentParser()
    get_application_xml_parser.add_argument(
        "-ci", "--ciID", action="store", type=str, required=True, help="CI_ID"
    )

    @cmd2.as_subcommand_to("get", "application-xml", get_application_xml_parser)
    def get_application_xml(self, ns: argparse.Namespace):
        console.print(self.applications.get_xml(ns.ciID))

    del_application_parser = cmd2.Cmd2ArgumentParser()
    del_application_parser.add_argument(
        "-ci", "--ciID", action="store", type=str, required=True, help="CI_ID"
    )

    @cmd2.as_subcommand_to("del", "application", del_application_parser)
    def del_application(self, ns: argparse.Namespace):
        self.applications.remove(ns.ciID)
