from enum import Enum
from typing import Optional

from wmipg.common import WMIConnector

REG_MAP = {
    "HKU": 2147483651,
    "HKLM": 2147483650,
}


def parse_reg_key(key_name) -> tuple[int, str]:
    components = key_name.split("\\")
    path = "\\".join(components[1:])
    hive = REG_MAP[components[0].upper()]
    return hive, path


class RegValueTypeEnum(Enum):
    binary = "binary"
    dword = "dword"
    qword = "qword"
    string = "string"

    @staticmethod
    def from_string(s):
        try:
            return RegValueTypeEnum[s]
        except KeyError:
            raise ValueError()


class RegValueReturnTypeEnum(Enum):
    REG_SZ = 1
    REG_EXPAND_SZ = 2
    REG_BINARY = 3
    REG_DWORD = 4
    REG_MULTI_SZ = 7
    REG_QWORD = 11


class Registry:
    wmi: WMIConnector

    def __init__(self, wmi_connector: WMIConnector):
        self.wmi = wmi_connector

    def get(self, _: str):
        return self.wmi.get_class_instances("SMS_Query")

    def enum(self):
        srp, _ = self.wmi.iWbemServices.GetObject("StdRegProv")
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

        return winscp_res

    def _reg_query_value(
        self, srp, key_name: str, value: Optional[str], type: RegValueTypeEnum
    ):
        hive, path = parse_reg_key(key_name)
        res = None

        match type:
            case RegValueTypeEnum.binary:
                res = srp.GetBinaryValue(hive, path, value).sValue

            case RegValueTypeEnum.dword:
                res = srp.GetDWORDValue(hive, path, value).uValue

            case RegValueTypeEnum.qword:
                res = srp.GetQWORDValue(hive, path, value).sValue

            case RegValueTypeEnum.string:
                res = srp.GetStringValue(hive, path, value).sValue

        return res

    def _reg_enum_path(self, srp, key_name):
        hive, path = parse_reg_key(key_name)
        output = []

        if keys := srp.EnumKey(hive, path).sNames:
            key_name_stripped = key_name.rstrip('\\') + "\\"
            output.extend([f"{key_name_stripped}{x}" for x in keys])

        values = srp.EnumValues(hive, path)
        if values.sNames:
            for name, _vtype in zip(values.sNames, values.Types):
                vtype = RegValueReturnTypeEnum(_vtype)
                output.append(f"{name}\t{vtype.name}")

        return "\n".join(output)

    def query(self, key_name: str, value: Optional[str], type: RegValueTypeEnum):
        srp, _ = self.wmi.iWbemServices.GetObject("StdRegProv")

        if value:
            return self._reg_query_value(srp, key_name, value, type)
        else:
            return self._reg_enum_path(srp, key_name)

    def set_value(
        self, key_name: str, value: str, data: str | bytes, type: RegValueTypeEnum
    ):
        srp, _ = self.wmi.iWbemServices.GetObject("StdRegProv")
        hive, path = parse_reg_key(key_name)

        res = None

        match type:
            case RegValueTypeEnum.binary:
                res = srp.SetBinaryValue(hive, path, value, data)

            case RegValueTypeEnum.dword:
                res = srp.SetDWORDValue(hive, path, value, int(data))

            case RegValueTypeEnum.qword:
                res = srp.SetQWORDValue(hive, path, value, int(data))

            case RegValueTypeEnum.string:
                res = srp.SetStringValue(hive, path, value, data)

        return res

    def delete(self, key_name: str, value: str):
        srp, _ = self.wmi.iWbemServices.GetObject("StdRegProv")
        hive, path = parse_reg_key(key_name)

        return srp.DeleteValue(hive, path, value)
