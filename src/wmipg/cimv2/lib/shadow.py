from enum import Enum

from wmipg.common import WMIConnector


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


class Shadow:
    wmi: WMIConnector

    def __init__(self, wmi_connector: WMIConnector):
        self.wmi = wmi_connector

    def list(self):
        return self.wmi.get_class_instances_raw(
            "Select ID,DeviceObject,InstallDate,VolumeName,State,Persistent FROM Win32_ShadowCopy"
        )

    def create(self, volume: str):
        shadow, _ = self.wmi.iWbemServices.GetObject("Win32_ShadowCopy")
        return shadow.Create(volume, "ClientAccessible")

    def delete(self, id: str):
        return self.wmi.iWbemServices.DeleteInstance(f"Win32_ShadowCopy.ID='{id}'")
