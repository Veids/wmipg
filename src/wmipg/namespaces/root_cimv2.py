import re
import cmd2
import argparse

from impacket import system_errors
from rich import print, print_json
from rich.table import Table
from datetime import datetime, timedelta
from enum import Enum

from wmipg.common import console, print_data, columnFormatter, load_security_definitions


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


class RegValueTypeEnum(Enum):
    binary = "binary"
    dword = "dword"
    qword = "qword"
    string = "string"


class RegValueReturnTypeEnum(Enum):
    REG_SZ = 1
    REG_EXPAND_SZ = 2
    REG_BINARY = 3
    REG_DWORD = 4
    REG_MULTI_SZ = 7
    REG_QWORD = 11


REG_MAP = {
    "HKU": 2147483651,
    "HKLM": 2147483650,
}


def parse_reg_key(key_name) -> tuple[int, str]:
    components = key_name.split("\\")
    path = "\\".join(components[1:])
    hive = REG_MAP[components[0].upper()]
    return hive, path


@cmd2.with_default_category("WMI")
class CIMv2(cmd2.CommandSet):
    paths = ["root/cimv2"]

    def __init__(self, connector):
        super().__init__()
        self.connector = connector
        self.subcmds = list()
        self._secs = load_security_definitions()

    def check_namespace(self, namespace: str) -> bool:
        return namespace in self.paths

    def load_subcommands(self, _: cmd2.Cmd):
        pass

    def unload_subcommands(self, _: cmd2.Cmd):
        pass

    def _print_detections(self, detections: list):
        if detections:
            print("Found security tools:")
            for x in detections:
                print(f"\t{x['process']} - {x['long']}")

    def do_pslist(self, _):
        """Get process list"""

        res = self.connector.get_class_instances_raw("Select * FROM Win32_Process")
        detections = []

        table = Table(title="Netstat")
        table.add_column("Name")
        table.add_column("SessionId")
        table.add_column("PID")
        table.add_column("PPID")
        table.add_column("CommandLine")
        table.add_column("Owner")

        res = sorted(res, key=lambda x: x.SessionId)

        for x in res:
            owner = x.GetOwner()
            if owner.User is None and owner.Domain is None:
                owner = "-"
            else:
                owner = str(owner.Domain) + "\\" + str(owner.User)

            name = str(x.Name)
            if name.lower() in self._secs:
                detections.append(self._secs[name.lower()])
                name = f"[red]{name}[/red]"

            table.add_row(
                name,
                str(x.SessionId),
                str(x.ProcessId),
                str(x.ParentProcessId),
                str(x.CommandLine),
                owner,
            )

        console.print(table)
        self._print_detections(detections)

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

    reg_parser = cmd2.Cmd2ArgumentParser(description="StdRegProv operations")
    reg_subparsers = reg_parser.add_subparsers(title="entity", help="Command")

    @cmd2.with_argparser(reg_parser)
    def do_reg(self, ns: argparse.Namespace):
        handler = ns.cmd2_handler.get()
        if handler is not None:
            handler(ns)
        else:
            self.do_help("reg")

    reg_enum_parser = cmd2.Cmd2ArgumentParser(
        description="Enumerate juicy registry content (WinSCP)"
    )

    @cmd2.as_subcommand_to("reg", "enum", reg_enum_parser)
    def reg_enum(self, _):
        srp, _ = self.connector.iWbemServices.GetObject("StdRegProv")
        hku = REG_MAP["HKU"]
        users = srp.EnumKey(hku, "").sNames

        winscp = r"Software\Martin Prikryl\WinSCP 2\Sessions"
        winscp_res = {}
        for user in users:
            path = "%s\\%s" % (user, winscp)
            sessions = srp.EnumKey(hku, path).sNames
            if sessions:
                winscp_res[user] = {}
                for session in sessions:
                    spath = rf"{path}\{session}"
                    winscp_res[user][session] = {
                        "HostName": srp.GetStringValue(hku, spath, "HostName").sValue,
                        "Password": srp.GetStringValue(hku, spath, "Password").sValue,
                        "UserName": srp.GetStringValue(hku, spath, "UserName").sValue,
                    }

        print(winscp_res)

    def _reg_query_value(self, srp, ns):
        srp, _ = self.connector.iWbemServices.GetObject("StdRegProv")

        hive, path = parse_reg_key(ns.key_name)
        res = None

        match ns.type:
            case RegValueTypeEnum.binary:
                res = srp.GetBinaryValue(hive, path, ns.value).sValue

            case RegValueTypeEnum.dword:
                res = srp.GetDWORDValue(hive, path, ns.value).sValue

            case RegValueTypeEnum.qword:
                res = srp.GetQWORDValue(hive, path, ns.value).sValue

            case RegValueTypeEnum.string:
                res = srp.GetStringValue(hive, path, ns.value).sValue

        print(res)

    def _reg_enum_path(self, srp, ns):
        hive, path = parse_reg_key(ns.key_name)
        output = []

        if keys := srp.EnumKey(hive, path).sNames:
            output.extend([f"{ns.key_name.rstrip('\\')}\\{x}" for x in keys])

        values = srp.EnumValues(hive, path)
        if values.sNames:
            for name, _vtype in zip(values.sNames, values.Types):
                vtype = RegValueReturnTypeEnum(_vtype)
                output.append(f"{name}\t{vtype.name}")

        print("\n".join(output))

    reg_query_parser = cmd2.Cmd2ArgumentParser(description="Query registry")
    reg_query_parser.add_argument("key_name", type=str)
    reg_query_parser.add_argument("-v", "--value", type=str, required=False)
    reg_query_parser.add_argument(
        "-t",
        "--type",
        type=RegValueTypeEnum,
        choices=list(RegValueTypeEnum),
        default=RegValueTypeEnum.string,
    )

    @cmd2.as_subcommand_to("reg", "query", reg_query_parser)
    def reg_query(self, ns: argparse.Namespace):
        srp, _ = self.connector.iWbemServices.GetObject("StdRegProv")

        if ns.value:
            self._reg_query_value(srp, ns)
        else:
            self._reg_enum_path(srp, ns)

    def do_loggedon(self, _):
        """Enumerated currently logged-on users"""

        print_data(
            self.connector.get_class_instances_raw("Select * From Win32_LoggedOnUser")
        )

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

        request = [
            "Select TimeGenerated,InsertionStrings FROM Win32_NTLogEvent WHERE Logfile='Security' AND EventCode='4624'"
        ]

        if ns.days != 0:
            timeGenerated = datetime.now() - timedelta(days=ns.days)
            timeGenerated = timeGenerated.strftime("%Y%m%d%H%M%S.000000-000")

            request.append(f"AND TimeGenerated > '{timeGenerated}'")

        if ns.login is not None:
            request.append(f"AND Message LIKE '%{ns.login}%'")

        events = self.connector.get_class_instances_raw(" ".join(request))

        table = Table(title="Win32_NTLogEvent")
        table.add_column("TimeGenerated")
        table.add_column("Source IP")
        table.add_column("Login")
        table.add_column("LP")
        table.add_column("AP")

        for event in events:
            login, domain, ap, lp, ip = self._parse_insertion_strings(event.InsertionStrings)

            date = str(
                datetime.strptime(event.TimeGenerated.split(".")[0], "%Y%m%d%H%M%S")
            )
            table.add_row(date, ip, f"{domain}\\{login}", lp, ap)

        console.print(table)

    def do_shares(self, _):
        """List windows shares"""

        print_data(self.connector.get_class_instances_raw("Select * FROM Win32_Share"))

    def do_profiles(self, _):
        """List local user profiles"""

        print_data(
            self.connector.get_class_instances_raw(
                "Select SID,LocalPath,Special,LastUseTime from Win32_UserProfile"
            )
        )

    ping_parser = cmd2.Cmd2ArgumentParser(
        description="Get ping result of a remote system"
    )
    ping_parser.add_argument(
        "address", action="store", type=str, help="Address to ping"
    )

    @cmd2.with_argparser(ping_parser)
    def do_ping(self, ns: argparse.Namespace):
        def pingFormatter(prop, obj):
            value = prop["value"]
            if prop["name"] == "StatusCode":
                name = PingStatusCode(value).name.replace("_", " ")
                return f"{name} ({value})"

            return value

        print_data(
            self.connector.get_class_instances_raw(
                f"Select Address,StatusCode,ResponseTime,Timeout FROM Win32_PingStatus WHERE Address='{ns.address}'"
            ),
            customFormatter=pingFormatter,
        )

    shadow_parser = cmd2.Cmd2ArgumentParser(description="Interact with shadow copies")
    shadow_subparsers = shadow_parser.add_subparsers(
        title="action", help="shadow operation"
    )

    @cmd2.with_argparser(shadow_parser)
    def do_shadow(self, ns: argparse.Namespace):
        handler = ns.cmd2_handler.get()
        if handler is not None:
            handler(ns)
        else:
            self._cmd.do_help("shadow")

    shadow_list_parser = cmd2.Cmd2ArgumentParser(description="Enumerate shadow copies")

    @cmd2.as_subcommand_to("shadow", "list", shadow_list_parser)
    def shadow_list(self, _):
        def shadowListFormatter(prop, obj):
            value = prop["value"]
            if prop["name"] == "State":
                name = ShadowStates(value).name
                return f"{name} ({value})"

            return value

        print_data(
            self.connector.get_class_instances_raw(
                "Select ID,DeviceObject,InstallDate,VolumeName,State,Persistent FROM Win32_ShadowCopy"
            ),
            customFormatter=shadowListFormatter,
        )

    shadow_create_parser = cmd2.Cmd2ArgumentParser(description="Create a shadow copy")
    shadow_create_parser.add_argument(
        "volume", action="store", type=str, help="Target volume"
    )

    @cmd2.as_subcommand_to("shadow", "create", shadow_create_parser)
    def shadow_create(self, ns: argparse.Namespace):
        shadow, _ = self.connector.iWbemServices.GetObject("Win32_ShadowCopy")
        res = shadow.Create(ns.volume, "ClientAccessible")
        print(f"Created {res.ShadowID}")

    shadow_delete_parser = cmd2.Cmd2ArgumentParser(description="Remove a shadow copy")
    shadow_delete_parser.add_argument(
        "ID", action="store", type=str, help="Target ShadowID"
    )

    @cmd2.as_subcommand_to("shadow", "delete", shadow_delete_parser)
    def shadow_delete(self, ns: argparse.Namespace):
        self.connector.checkiWbemResponse(
            f"Removing shadow {ns.ID}",
            self.connector.iWbemServices.DeleteInstance(
                'Win32_ShadowCopy.ID="%s"' % ns.ID
            ),
        )

    def do_volumes(self, _):
        """Get volumes list"""

        print_data(
            self.connector.get_class_instances_raw(
                "Select DriveLetter,DeviceID,FileSystem,SystemVolume,Capacity,Label FROM Win32_Volume"
            )
        )

    ls_parser = cmd2.Cmd2ArgumentParser(description="List directory content")
    ls_parser.add_argument("path", action="store", type=str, help="c:\\")

    @cmd2.with_argparser(ls_parser)
    def do_ls(self, ns: argparse.Namespace):
        drive, path = ns.path.split(":")
        path = path.replace("\\", r"\\")

        directories = self.connector.get_class_instances_raw(
            f"SELECT Caption,CreationDate,LastAccessed,FileSize FROM CIM_Directory Where Drive='{drive}:' and PATH='{path}'"
        )
        files = self.connector.get_class_instances_raw(
            f"SELECT Caption,CreationDate,LastAccessed,FileSize,Version FROM CIM_DataFile Where Drive='{drive}:' and PATH='{path}'"
        )

        columns = ["Caption", "CreationDate", "LastAccessed", "FileSize", "Version"]
        table = Table(*columns, title="Directory content")

        for obj in directories + files:
            props = obj.getProperties()
            row = []

            for column in columns:
                if prop := props.get(column):
                    row.append(columnFormatter(prop, obj))
                else:
                    row.append("")

            table.add_row(*row)

        console.print(table)

    stat_parser = cmd2.Cmd2ArgumentParser(description="Get info about particular file")
    stat_parser.add_argument("path", action="store", type=str, help="c:\\log.txt")

    @cmd2.with_argparser(stat_parser)
    def do_stat(self, ns: argparse.Namespace):
        path = ns.path.replace("\\", r"\\")
        obj, _ = self.connector.iWbemServices.GetObject(f"CIM_DataFile.Name='{path}'")
        print_data([obj], style="column")

    mv_parser = cmd2.Cmd2ArgumentParser(description="Move/Rename a file")
    mv_parser.add_argument("source", action="store", type=str, help="C:\\log.txt")
    mv_parser.add_argument("dest", action="store", type=str, help="C:\\log2.txt")

    @cmd2.with_argparser(mv_parser)
    def do_mv(self, ns: argparse.Namespace):
        source = ns.source.replace("\\", r"\\")
        dest = ns.dest.replace("\\", r"\\")

        # TIPS: will fail if Name='' contains double quotes
        obj, _ = self.connector.iWbemServices.GetObject(f"CIM_DataFile.Name='{source}'")
        res = obj.Rename(dest)
        rv = res.ReturnValue
        msg = " - ".join(system_errors.ERROR_MESSAGES[rv])

        print(f"Result {rv}: {msg}")

    cp_parser = cmd2.Cmd2ArgumentParser(description="Copy a file")
    cp_parser.add_argument("source", action="store", type=str, help="C:\\log.txt")
    cp_parser.add_argument("dest", action="store", type=str, help="C:\\log2.txt")

    @cmd2.with_argparser(cp_parser)
    def do_cp(self, ns: argparse.Namespace):
        source = ns.source.replace("\\", r"\\")
        dest = ns.dest.replace("\\", r"\\")

        # TIPS: will fail if Name='' contains double quotes
        obj, _ = self.connector.iWbemServices.GetObject(f"CIM_DataFile.Name='{source}'")
        res = obj.Copy(dest)
        rv = res.ReturnValue
        msg = " - ".join(system_errors.ERROR_MESSAGES[rv])

        print(f"Result {rv}: {msg}")

    rm_parser = cmd2.Cmd2ArgumentParser(description="Remove a file")
    rm_parser.add_argument("path", action="store", type=str, help="C:\\log.txt")

    @cmd2.with_argparser(rm_parser)
    def do_rm(self, ns: argparse.Namespace):
        path = ns.path.replace("\\", r"\\")

        # TIPS: will fail if Name='' contains double quotes
        obj, _ = self.connector.iWbemServices.GetObject(f"CIM_DataFile.Name='{path}'")
        res = obj.Delete()
        rv = res.ReturnValue
        msg = " - ".join(system_errors.ERROR_MESSAGES[rv])

        print(f"Result {rv}: {msg}")

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
        query = "Select Name,State,ProcessID,PathName,StartMode FROM WIN32_Service"

        if not ns.all:
            query = f'{query} Where State="Running"'

        detections = []

        def serviceFormatter(prop, obj):
            value = prop["value"]
            if prop["name"] == "PathName":
                name = value.replace('"', "").split("\\")[-1].split(" ")[0].lower()
                if name in self._secs:
                    detections.append(self._secs[name])
                    return f"[red]{value}[/red]"

            return value

        print_data(
            self.connector.get_class_instances_raw(query),
            customFormatter=serviceFormatter,
        )
        self._print_detections(detections)
