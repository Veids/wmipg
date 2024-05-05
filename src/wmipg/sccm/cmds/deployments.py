import cmd2
import argparse

from wmipg.sccm.lib import Deployments
from wmipg.common import print_data


@cmd2.with_default_category("Deployments")
class DeploymentsCMD(cmd2.CommandSet):
    deployments: Deployments

    def __init__(self, wmi_connector):
        super().__init__()
        self.deployments = Deployments(wmi_connector)

    add_deployment_parser = cmd2.Cmd2ArgumentParser()
    add_deployment_parser.add_argument(
        "-s", "--siteCode", action="store", type=str, required=True
    )
    add_deployment_parser.add_argument(
        "-an",
        "--applicationName",
        action="store",
        type=str,
        required=True,
        help="Name of the application",
    )
    add_deployment_parser.add_argument(
        "-ai",
        "--applicationCIID",
        action="append",
        type=int,
        required=True,
        help="CI_ID of the application (May be specified multiple times)",
    )
    add_deployment_parser.add_argument(
        "-cn",
        "--collectionName",
        action="store",
        type=str,
        required=True,
        help="Name of the collection",
    )
    add_deployment_parser.add_argument(
        "-ci",
        "--collectionID",
        action="store",
        type=str,
        required=True,
        help="ID of the collection",
    )

    @cmd2.as_subcommand_to("add", "deployment", add_deployment_parser)
    def add_deployment(self, ns: argparse.Namespace):
        _ = self.deployments.add(
            ns.siteCode,
            ns.applicationName,
            ns.applicationCIID,
            ns.collectionName,
            ns.collectionID,
        )

    get_deployment_parser = cmd2.Cmd2ArgumentParser()
    get_deployment_parser.add_argument(
        "-a",
        "--applicationName",
        action="store",
        type=str,
        default=None,
        help="Name of the application",
    )
    get_deployment_parser.add_argument(
        "-ci",
        "--collectionID",
        action="store",
        type=str,
        default=None,
        help="ID of the collection",
    )
    get_deployment_parser.add_argument(
        "-p",
        "--property",
        action="append",
        type=str,
        default=None,
        help="Property to output",
    )

    @cmd2.as_subcommand_to("get", "deployment", get_deployment_parser)
    def get_deployment(self, ns: argparse.Namespace):
        deployments = self.deployments.get(
            ns.applicationName, ns.collectionID, ns.property
        )
        print_data(deployments)

    del_deployment_parser = cmd2.Cmd2ArgumentParser()
    del_deployment_parser.add_argument(
        "-ai",
        "--assignmentID",
        action="store",
        type=str,
        default=None,
        required=True,
        help="ID of the assignment",
    )

    @cmd2.as_subcommand_to("del", "deployment", del_deployment_parser)
    def del_deployment(self, ns: argparse.Namespace):
        self.deployments.remove(ns.assignmentID)
