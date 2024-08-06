import cmd2
import argparse

from enum import Enum

from wmipg.common import print_data, load_security_definitions
from wmipg.cimv2.lib.service import Service, SERVICE_CONTROL_RETURN


class ServiceStartModeEnum(Enum):
    boot = "Boot"
    system = "System"
    auto = "Automatic"
    manual = "Manual"
    disabled = "Disabled"

    @staticmethod
    def from_string(s):
        try:
            return ServiceStartModeEnum[s]
        except KeyError:
            raise ValueError()


@cmd2.with_default_category("Execution")
class ServiceCMD(cmd2.CommandSet):
    service: Service

    def __init__(self, wmi_connector):
        super().__init__()
        self.service = Service(wmi_connector)
        self._secs = load_security_definitions()

    def _print_detections(self, detections: list):
        if detections:
            print("Found security tools:")
            for x in detections:
                print(f"\t{x['process']} - {x['long']}")

    service_parser = cmd2.Cmd2ArgumentParser(description="Interact with services")
    service_subparsers = service_parser.add_subparsers(
        title="action", help="service operation"
    )

    @cmd2.with_argparser(service_parser)
    def do_service(self, ns: argparse.Namespace):
        handler = ns.cmd2_handler.get()
        if handler is not None:
            handler(ns)
        else:
            self._cmd.do_help("service")

    service_list_parser = cmd2.Cmd2ArgumentParser(description="Enumerate services")
    service_list_parser.add_argument(
        "-a",
        "--all",
        default=False,
        action=argparse.BooleanOptionalAction,
        help="Print all services, not only running",
    )

    @cmd2.as_subcommand_to("service", "list", service_list_parser)
    def service_list(self, ns: argparse.Namespace):
        detections = []

        def serviceFormatter(prop, _):
            value = prop["value"]
            if prop["name"] == "PathName":
                name = value.replace('"', "").split("\\")[-1].split(" ")[0].lower()
                if name in self._secs:
                    detections.append(self._secs[name])
                    return f"[red]{value}[/red]"

            return value

        print_data(
            self.service.list(ns.all),
            customFormatter=serviceFormatter,
        )
        self._print_detections(detections)

    service_start_parser = cmd2.Cmd2ArgumentParser(description="Start a service")
    service_start_parser.add_argument(
        "name",
        help="Service name",
    )

    @cmd2.as_subcommand_to("service", "start", service_start_parser)
    def service_start(self, ns: argparse.Namespace):
        res = self.service.start(ns.name)
        rv = res.ReturnValue
        print(f"Result: {rv} - {SERVICE_CONTROL_RETURN[rv]}")

    service_stop_parser = cmd2.Cmd2ArgumentParser(description="Stop a service")
    service_stop_parser.add_argument(
        "name",
        help="Service name",
    )

    @cmd2.as_subcommand_to("service", "stop", service_stop_parser)
    def service_stop(self, ns: argparse.Namespace):
        res = self.service.stop(ns.name)
        rv = res.ReturnValue
        print(f"Result: {rv} - {SERVICE_CONTROL_RETURN[rv]}")

    service_change_start_mode_parser = cmd2.Cmd2ArgumentParser(
        description="Change start method of a service"
    )
    service_change_start_mode_parser.add_argument(
        "name",
        help="Service name",
    )
    service_change_start_mode_parser.add_argument(
        "mode",
        type=ServiceStartModeEnum.from_string,
        choices=tuple(ServiceStartModeEnum),
        help="Service name",
    )

    @cmd2.as_subcommand_to(
        "service", "change_start_mode", service_change_start_mode_parser
    )
    def service_change_start_method(self, ns: argparse.Namespace):
        res = self.service.change_start_mode(ns.name, ns.mode.value)
        rv = res.ReturnValue
        print(f"Result: {rv} - {SERVICE_CONTROL_RETURN[rv]}")
