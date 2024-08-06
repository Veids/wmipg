import cmd2

from wmipg.cimv2.cmds import (
    RegistryCMD,
    ServiceCMD,
    ShareCMD,
    FileOperationCMD,
    ShadowCMD,
    ProcessCMD,
    UserCMD,
    GenericCMD,
)


@cmd2.with_default_category("WMI")
class CIMv2(cmd2.CommandSet):
    paths = ["root/cimv2"]

    def __init__(self, connector):
        super().__init__()
        self.connector = connector
        self.subcmds = [
            RegistryCMD(connector),
            ServiceCMD(connector),
            ShareCMD(connector),
            FileOperationCMD(connector),
            ShadowCMD(connector),
            ProcessCMD(connector),
            UserCMD(connector),
            GenericCMD(connector),
        ]

    def check_namespace(self, namespace: str) -> bool:
        return namespace in self.paths

    def load_subcommands(self, cmd: cmd2.Cmd):
        for x in self.subcmds:
            cmd.register_command_set(x)

    def unload_subcommands(self, cmd: cmd2.Cmd):
        for x in self.subcmds:
            cmd.unregister_command_set(x)
