from wmipg.common import WMIConnector


class Process:
    wmi: WMIConnector

    def __init__(self, wmi_connector: WMIConnector):
        self.wmi = wmi_connector

    def list(self):
        return self.wmi.get_class_instances_raw("Select * FROM Win32_Process")
