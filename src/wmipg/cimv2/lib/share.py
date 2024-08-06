from enum import Enum, Flag, IntEnum

from wmipg.common import WMIConnector


class ShareTypeEnum(Enum):
    DISK_DRIVE = 0
    PRINT_QUEUE = 1
    DEVICE = 2
    IPC = 3
    DISK_DRIVE_ADMIN = 2147483648
    PRINT_QUEUE_ADMIN = 2147483649
    DEVICE_ADMIN = 2147483650
    IPC_ADMIN = 2147483651

    @staticmethod
    def from_string(s):
        try:
            return ShareTypeEnum[s]
        except KeyError:
            raise ValueError()


class ShareCreateReturnEnum(IntEnum):
    SUCCESS = 0
    ACCESS_DENIED = 2
    UNKNOWN_FAILURE = 8
    INVALID_NAME = 9
    INVALID_LEVEL = 10
    INVLAID_PARAMETER = 21
    DUPLICATE_SHARE = 22
    REDIRECTED_PATH = 23
    UNKOWN_DEVICE_OR_DIRECTORY = 24
    NET_NAME_NOT_FOUND = 25


class ShareAccessMaskFlag(Flag):
    FILE_LIST_DIRECTORY = 1
    FILE_ADD_FILE = 2
    FILE_ADD_SUBDIRECTORY = 4
    FILE_READ_EA = 8
    FILE_WRITE_EA = 16
    FILE_TRAVERSE = 32
    FILE_DELETE_CHILD = 64
    FILE_READ_ATTRIBUTES = 128
    FILE_WRITE_ATTRIBUTES = 256
    DELETE = 0x10000
    READ_CONTROL = 0x20000
    WRITE_DAC = 0x40000
    WRITE_OWNER = 0x80000
    SYNCHRONIZE = 0x100000


class Share:
    wmi: WMIConnector

    def __init__(self, wmi_connector: WMIConnector):
        self.wmi = wmi_connector

    def list(self):
        return self.wmi.get_class_instances_raw("Select * FROM Win32_Share")

    def create(
        self, path: str, name: str, type: int, description: str = "", password: str = ""
    ) -> ShareCreateReturnEnum:
        share, _ = self.wmi.iWbemServices.GetObject("Win32_Share")
        res = share.Create(path, name, type, 0, description, password, None)
        r = ShareCreateReturnEnum(res.ReturnValue)
        return r

    def delete(self, name: str):
        return self.wmi.iWbemServices.DeleteInstance(f"Win32_Share.Name='{name}'")

    def get_access_mask(self, name: str) -> ShareAccessMaskFlag:
        share, _ = self.wmi.iWbemServices.GetObject(f"Win32_Share.Name='{name}'")
        am = share.GetAccessMask().ReturnValue
        amf = ShareAccessMaskFlag(am)
        return amf
