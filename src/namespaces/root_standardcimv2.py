import cmd2

from rich.table import Table

import src.common as common


@cmd2.with_default_category('WMI')
class StandardCimv2(cmd2.CommandSet):
    paths = [
        "root/standardcimv2"
    ]

    def __init__(self, connector):
        super().__init__()
        self.connector = connector

    def do_netstat(self, _):
        """Get connections info"""

        columns = ["OwningProcess", "LocalAddress", "LocalPort", "RemoteAddress", "RemotePort"]
        res = self.connector.get_class_instances_raw("Select %s FROM MSFT_NetTCPConnection" % ",".join(columns))
        table = Table(title="MSFT_NetTCPConnection")
        for x in columns:
            table.add_column(x)

        res = sorted(res, key = lambda x: x.LocalAddress)
        for x in res:
            table.add_row(str(x.OwningProcess), str(x.LocalAddress), str(x.LocalPort), str(x.RemoteAddress), str(x.RemotePort))

        common.console.print(table)

    def do_ipconfig(self, _):
        """Get interface list along with assigned IP address"""

        common.print_data(
            self.connector.get_class_instances_raw(
                "Select InterfaceIndex,InterfaceAlias,IPAddress FROM MSFT_NetIPAddress"
            )
        )
