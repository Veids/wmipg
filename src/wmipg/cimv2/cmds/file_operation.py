import cmd2
import argparse

from rich.table import Table
from impacket import system_errors

from wmipg.common import WMIConnector, print_data, console, print_data, columnFormatter
from wmipg.cimv2.lib.file_operation import FileOperation


@cmd2.with_default_category("File operations")
class FileOperationCMD(cmd2.CommandSet):
    file_operation: FileOperation
    wmi: WMIConnector

    def __init__(self, wmi_connector):
        super().__init__()
        self.file_operation = FileOperation(wmi_connector)
        self.wmi = wmi_connector

    def do_volumes(self, _):
        """Get volumes list"""

        print_data(self.file_operation.list_volumes())

    ls_parser = cmd2.Cmd2ArgumentParser(description="List directory content")
    ls_parser.add_argument("path", action="store", type=str, help="c:\\")

    @cmd2.with_argparser(ls_parser)
    def do_ls(self, ns: argparse.Namespace):
        directories, files = self.file_operation.list_files(ns.path)

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
        obj = self.file_operation.stat(ns.path)
        print_data([obj], style="column")

    mv_parser = cmd2.Cmd2ArgumentParser(description="Move/Rename a file")
    mv_parser.add_argument("source", action="store", type=str, help="C:\\log.txt")
    mv_parser.add_argument("dest", action="store", type=str, help="C:\\log2.txt")

    @cmd2.with_argparser(mv_parser)
    def do_mv(self, ns: argparse.Namespace):
        res = self.file_operation.mv(ns.source, ns.dest)
        rv = res.ReturnValue
        msg = " - ".join(system_errors.ERROR_MESSAGES[rv])

        print(f"Result {rv}: {msg}")

    cp_parser = cmd2.Cmd2ArgumentParser(description="Copy a file")
    cp_parser.add_argument("source", action="store", type=str, help="C:\\log.txt")
    cp_parser.add_argument("dest", action="store", type=str, help="C:\\log2.txt")

    @cmd2.with_argparser(cp_parser)
    def do_cp(self, ns: argparse.Namespace):
        res = self.file_operation.cp(ns.source, ns.dest)
        rv = res.ReturnValue
        msg = " - ".join(system_errors.ERROR_MESSAGES[rv])

        print(f"Result {rv}: {msg}")

    rm_parser = cmd2.Cmd2ArgumentParser(description="Remove a file")
    rm_parser.add_argument("path", action="store", type=str, help="C:\\log.txt")

    @cmd2.with_argparser(rm_parser)
    def do_rm(self, ns: argparse.Namespace):
        res = self.file_operation.rm(ns.path)
        rv = res.ReturnValue
        msg = " - ".join(system_errors.ERROR_MESSAGES[rv])

        print(f"Result {rv}: {msg}")
