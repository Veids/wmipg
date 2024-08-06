import cmd2
import argparse

from datetime import datetime
from rich.table import Table

from wmipg.cimv2.lib.user import User
from wmipg.common import print_data, console


@cmd2.with_default_category("Users/Sessions")
class UserCMD(cmd2.CommandSet):
    user: User

    def __init__(self, wmi_connector):
        super().__init__()
        self.user = User(wmi_connector)

    def do_users(self, _):
        """Get local users list (net user)"""

        print_data(self.user.local_users())

    def do_loggedon(self, _):
        """Enumerated currently logged-on users"""

        print_data(self.user.loggedon())

    login_history_parser = cmd2.Cmd2ArgumentParser()
    login_history_parser.add_argument(
        "-l", "--login", action="store", type=str, default=None, help="Target username"
    )
    login_history_parser.add_argument(
        "-d",
        "--days",
        action="store",
        type=int,
        default=7,
        help="Days delta (0 means all)",
    )

    def _parse_insertion_strings(self, iss):
        login = iss[5]
        domain = iss[6]
        ap = iss[9]
        lp = iss[10]
        ip = iss[18]

        return login, domain, ap, lp, ip

    @cmd2.with_argparser(login_history_parser)
    def do_logon_history(self, ns: argparse.Namespace):
        """Print users logon history information"""

        events = self.user.logon_history(ns.login, ns.days)

        table = Table(title="Win32_NTLogEvent")
        table.add_column("TimeGenerated")
        table.add_column("Source IP")
        table.add_column("Login")
        table.add_column("LP")
        table.add_column("AP")

        for event in events:
            login, domain, ap, lp, ip = self._parse_insertion_strings(
                event.InsertionStrings
            )

            date = str(
                datetime.strptime(event.TimeGenerated.split(".")[0], "%Y%m%d%H%M%S")
            )
            table.add_row(date, ip, f"{domain}\\{login}", lp, ap)

        console.print(table)

    def do_profiles(self, _):
        """List local user profiles"""

        print_data(self.user.profiles())
