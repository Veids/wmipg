import cmd2

from wmipg.common import print_data

DEFINITIONS = {
    "AvailableSecurityProperties": [
        "If present, no relevant properties exist on the device.",
        "If present, hypervisor support is available.",
        "If present, Secure Boot is available.",
        "If present, DMA protection is available.",
        "If present, Secure Memory Overwrite is available.",
        "If present, NX protections are available.",
        "If present, SMM mitigations are available.",
        "If present, MBEC/GMET is available.",
        "If present, APIC virtualization is available.",
    ]
}


@cmd2.with_default_category("WMI")
class DeviceGuard(cmd2.CommandSet):
    paths = ["root/microsoft/windows/deviceguard"]

    def __init__(self, connector):
        super().__init__()
        self.connector = connector
        self.subcmds = list()

    def check_namespace(self, namespace: str) -> bool:
        return namespace in self.paths

    def load_subcommands(self, _: cmd2.Cmd):
        pass

    def unload_subcommands(self, _: cmd2.Cmd):
        pass

    def do_device_guard(self, _):
        """Print DeviceGuard status"""
        res = self.connector.get_class_instances_raw(
            "Select AvailableSecurityProperties,RequiredSecurityProperties,SecurityServicesConfigured,SecurityServicesRunning,VirtualizationBasedSecurityStatus from WIN32_DeviceGuard"
        )
        print_data(res)

        asp = res[0].AvailableSecurityProperties
        print("AvailableSecurityProperties")
        for x in asp:
            desc = DEFINITIONS["AvailableSecurityProperties"][x]
            print(f"\t{x} - {desc}")
