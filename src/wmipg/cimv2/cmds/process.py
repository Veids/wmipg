import cmd2

from rich.table import Table

from wmipg.common import console, load_security_definitions
from wmipg.cimv2.lib.process import Process


@cmd2.with_default_category("Execution")
class ProcessCMD(cmd2.CommandSet):
    process: Process

    def __init__(self, wmi_connector):
        super().__init__()
        self.process = Process(wmi_connector)
        self._secs = load_security_definitions()

    def _print_detections(self, detections: list):
        if detections:
            print("Found security tools:")
            for x in detections:
                print(f"\t{x['process']} - {x['long']}")

    def do_pslist(self, _):
        """Get process list"""

        res = self.process.list()
        detections = []

        table = Table(title="Win32_Process")
        table.add_column("Name")
        table.add_column("SessionId")
        table.add_column("PID")
        table.add_column("PPID")
        table.add_column("CommandLine")
        table.add_column("Owner")

        res = sorted(res, key=lambda x: x.SessionId)

        for x in res:
            owner = x.GetOwner()
            if (owner and owner.User and owner.Domain) is None:
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
