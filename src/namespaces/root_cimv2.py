import re
import cmd2
import argparse

from cmd2 import CommandSet
from rich import print
from rich.table import Table
from datetime import datetime, timedelta
from enum import Enum

from src.common import console, print_data


class ShadowStates(Enum):
    # https://learn.microsoft.com/en-us/previous-versions/windows/desktop/legacy/aa394428(v=vs.85)
    Unknown = 0
    Preparing = 1
    ProcessingPrepare = 2
    Prepared = 3
    ProcessingPrecommit = 4
    Precommitted = 5
    ProcessingCommit = 6
    Committed = 7
    ProcessingPostcommit = 8
    Created = 9
    Aborted = 10
    Deleted = 11
    Count = 12


class PingStatusCode(Enum):
    # https://learn.microsoft.com/en-us/previous-versions/windows/desktop/wmipicmp/win32-pingstatus
    Success = 0
    Buffer_Too_Small = 11001
    Destination_Net_Unreachable = 11002
    Destination_Host_Unreachable = 11003
    Destination_Protocol_Unreachable = 11004
    Destination_Port_Unreachable = 11005
    No_Resources = 11006
    Bad_Option = 11007
    Hardware_Error = 11008
    Packet_Too_Big = 11009
    Request_Timed_Out = 11010
    Bad_Request = 11011
    Bad_Route = 11012
    TimeToLive_Expired_Transit = 11013
    TimeToLive_Expired_Reassembly = 11014
    Parameter_Problem = 11015
    Source_Quench = 11016
    Option_Too_Big = 11017
    Bad_Destination = 11018
    Negotiating_IPSEC = 11032
    General_Failure = 11050


@cmd2.with_default_category('WMI')
class CIMv2(CommandSet):
    paths = [
        "root/cimv2"
    ]

    def __init__(self, connector):
        super().__init__()
        self.connector = connector

    def do_pslist(self, _):
        """Get process list"""

        res = self.connector.get_class_instances_raw("Select * FROM Win32_Process")

        table = Table(title="Netstat")
        table.add_column("Name")
        table.add_column("SessionId")
        table.add_column("PID")
        table.add_column("PPID")
        table.add_column("CommandLine")
        table.add_column("Owner")

        res = sorted(res, key = lambda x: x.SessionId)

        for x in res:
            owner = x.GetOwner()
            if owner.User is None and owner.Domain is None:
                owner = "-"
            else:
                owner = str(owner.Domain) + "\\" + str(owner.User)

            table.add_row(str(x.Name), str(x.SessionId), str(x.ProcessId), str(x.ParentProcessId), str(x.CommandLine), owner)

        console.print(table)

    def do_users(self, _):
        """Get local users list (net user)"""

        print_data(
            self.connector.get_class_instances_raw(
                "Select Caption,LocalAccount,SID,Disabled,Lockout FROM Win32_UserAccount"
            )
        )

    def do_env(self, _):
        """Print environment variables"""

        print_data(
            self.connector.get_class_instances_raw(
                "Select Name,VariableValue,SystemVariable FROM Win32_Environment"
            )
        )

    def do_enum_registry(self, _):
        """Enumerate juicy registry content (WinSCP)"""

        srp, _ = self.connector.iWbemServices.GetObject("StdRegProv")
        HKU = 2147483651

        users = srp.EnumKey(HKU, "").sNames

        winscp = r"Software\Martin Prikryl\WinSCP 2\Sessions"
        winscp_res = {}
        for user in users:
            path = "%s\\%s" % (user, winscp)
            sessions = srp.EnumKey(HKU, path).sNames
            if sessions:
                winscp_res[user] = {}
                for session in sessions:
                    spath = rf"{path}\{session}"
                    winscp_res[user][session] = {
                        "HostName": srp.GetStringValue(HKU, spath, "HostName").sValue,
                        "Password": srp.GetStringValue(HKU, spath, "Password").sValue,
                        "UserName": srp.GetStringValue(HKU, spath, "UserName").sValue,
                    }

        print(winscp_res)

    def do_loggedon(self, _):
        """Enumerated currently logged-on users"""

        print_data(
            self.connector.get_class_instances_raw(
                "Select * From Win32_LoggedOnUser"
            )
        )

    login_history_parser = cmd2.Cmd2ArgumentParser()
    login_history_parser.add_argument('-l', '--login', action = 'store', type = str, default = None, help = 'Target username')
    login_history_parser.add_argument('-d', '--days', action = 'store', type = int, default = 7, help = 'Days delta (0 means all)')

    @cmd2.with_argparser(login_history_parser)
    def do_logon_history(self, ns: argparse.Namespace):
        """Print users logon history information"""

        request = ["Select TimeGenerated,Message FROM Win32_NTLogEvent WHERE Logfile='Security' AND EventCode='4624'"]

        if ns.days != 0:
            timeGenerated = datetime.now() - timedelta(days=ns.days)
            timeGenerated = timeGenerated.strftime("%Y%m%d%H%M%S.000000-000")

            request.append(f"AND TimeGenerated > '{timeGenerated}'")

        if ns.login is not None:
            request.append(f"AND Message LIKE '%{ns.login}%'")

        events = self.connector.get_class_instances_raw(
            " ".join(request)
        )
        ipmask = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        lpmask = r'Logon Process:(.*)'
        apmask = r'Authentication Package:(.*)'
        pnmask = r'Package Name (NTLM only):(.*)'
        loginmask = r'Account Name:(.*)'
        domainmask = r'Account Domain:(.*)'

        table = Table(title="Win32_NTLogEvent")
        table.add_column("TimeGenerated")
        table.add_column("Source IP")
        table.add_column("Login")
        table.add_column("LP")
        table.add_column("AP")
        table.add_column("PN")

        for event in events:
            source_ip = ",".join(re.findall(ipmask, event.Message))
            if source_ip == "":
                continue

            lp = ",".join(x.strip() for x in re.findall(lpmask, event.Message))
            ap = ",".join(x.strip() for x in re.findall(apmask, event.Message))
            pn = ",".join(x.strip() for x in re.findall(pnmask, event.Message))

            logins = re.findall(loginmask, event.Message)
            domains = re.findall(domainmask, event.Message)
            pairs = list(map(lambda l, d: f"{d.strip()}\\{l.strip()}", logins, domains))

            date = str(datetime.strptime(event.TimeGenerated.split('.')[0], "%Y%m%d%H%M%S"))
            table.add_row(date, pairs[1], source_ip, lp, ap, pn)

        console.print(table)

    def do_shares(self, _):
        """List windows shares"""

        print_data(
            self.connector.get_class_instances_raw(
                "Select * FROM Win32_Share"
            )
        )

    def do_profiles(self, _):
        """List local user profiles"""

        print_data(
            self.connector.get_class_instances_raw(
                "Select SID,LocalPath,Special,LastUseTime from Win32_UserProfile"
            )
        )

    ping_parser = cmd2.Cmd2ArgumentParser(description = "Get ping result of a remote system")
    ping_parser.add_argument('address', action = 'store', type = str, help = 'Address to ping')

    @cmd2.with_argparser(ping_parser)
    def do_ping(self, ns: argparse.Namespace):
        def pingFormatter(prop, obj):
            value = prop['value']
            if prop['name'] == "StatusCode":
                name = PingStatusCode(value).name.replace('_', ' ')
                return f"{name} ({value})"

            return value

        print_data(
            self.connector.get_class_instances_raw(
                f"Select Address,StatusCode,ResponseTime,Timeout FROM Win32_PingStatus WHERE Address='{ns.address}'"
            ),
            customFormatter = pingFormatter
        )

    shadow_parser = cmd2.Cmd2ArgumentParser(description = "Interact with shadow copies")
    shadow_subparsers = shadow_parser.add_subparsers(title='action', help='shadow operation')

    @cmd2.with_argparser(shadow_parser)
    def do_shadow(self, ns: argparse.Namespace):
        handler = ns.cmd2_handler.get()
        if handler is not None:
            handler(ns)
        else:
            self._cmd.do_help('shadow')

    shadow_list_parser = cmd2.Cmd2ArgumentParser(description = "Enumerate shadow copies")

    @cmd2.as_subcommand_to('shadow', 'list', shadow_list_parser)
    def shadow_list(self, _):
        def shadowListFormatter(prop, obj):
            value = prop['value']
            if prop['name'] == "State":
                name = ShadowStates(value).name
                return f"{name} ({value})"

            return value

        print_data(
            self.connector.get_class_instances_raw(
                "Select ID,DeviceObject,InstallDate,VolumeName,State,Persistent FROM Win32_ShadowCopy"
            ),
            customFormatter = shadowListFormatter
        )

    shadow_create_parser = cmd2.Cmd2ArgumentParser(description = "Create a shadow copy")
    shadow_create_parser.add_argument("volume", action = "store", type = str, help = "Target volume")

    @cmd2.as_subcommand_to("shadow", "create", shadow_create_parser)
    def shadow_create(self, ns: argparse.Namespace):
        shadow, _ = self.connector.iWbemServices.GetObject("Win32_ShadowCopy")
        res = shadow.Create(ns.volume, "ClientAccessible")
        print(f"Created {res.ShadowID}")

    shadow_delete_parser = cmd2.Cmd2ArgumentParser(description = "Remove a shadow copy")
    shadow_delete_parser.add_argument("ID", action = "store", type = str, help = "Target ShadowID")

    @cmd2.as_subcommand_to("shadow", "delete", shadow_delete_parser)
    def shadow_delete(self, ns: argparse.Namespace):
        self.connector.checkiWbemResponse(
            f"Removing shadow {ns.ID}",
            self.connector.iWbemServices.DeleteInstance('Win32_ShadowCopy.ID="%s"' % ns.ID)
        )

    def do_volumes(self, _):
        """Get volumes list"""

        print_data(
            self.connector.get_class_instances_raw(
                "Select DriveLetter,DeviceID,FileSystem,SystemVolume,Capacity,Label FROM Win32_Volume"
            )
        )
