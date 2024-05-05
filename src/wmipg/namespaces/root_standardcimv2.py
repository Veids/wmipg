import cmd2

from rich.table import Table

from wmipg.common import console, print_data


@cmd2.with_default_category("WMI")
class StandardCimv2(cmd2.CommandSet):
    paths = ["root/standardcimv2"]

    def __init__(self, connector):
        super().__init__()
        self.connector = connector

    def check_namespace(self, namespace: str) -> bool:
        return namespace in self.paths

    def load_subcommands(self, _: cmd2.Cmd):
        pass

    def unload_subcommands(self, _: cmd2.Cmd):
        pass

    def do_netstat(self, _):
        """Get connections info"""

        columns = [
            "OwningProcess",
            "LocalAddress",
            "LocalPort",
            "RemoteAddress",
            "RemotePort",
        ]
        res = self.connector.get_class_instances_raw(
            "Select %s FROM MSFT_NetTCPConnection" % ",".join(columns)
        )
        table = Table(title="MSFT_NetTCPConnection")
        for x in columns:
            table.add_column(x)

        res = sorted(res, key=lambda x: x.LocalAddress)
        for x in res:
            table.add_row(
                str(x.OwningProcess),
                str(x.LocalAddress),
                str(x.LocalPort),
                str(x.RemoteAddress),
                str(x.RemotePort),
            )

        console.print(table)

    def do_ipconfig(self, _):
        """Get interface list along with assigned IP address"""

        print_data(
            self.connector.get_class_instances_raw(
                "Select InterfaceIndex,InterfaceAlias,IPAddress FROM MSFT_NetIPAddress"
            )
        )
