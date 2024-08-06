from enum import Enum
from wmipg.common import WMIConnector


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


class Generic:
    wmi: WMIConnector

    def __init__(self, wmi_connector: WMIConnector):
        self.wmi = wmi_connector

    def env(self):
        return self.wmi.get_class_instances_raw(
            "Select Name,VariableValue,SystemVariable FROM Win32_Environment"
        )

    def ping(self, address: str):
        return self.wmi.get_class_instances_raw(
            f"Select Address,StatusCode,ResponseTime,Timeout FROM Win32_PingStatus WHERE Address='{address}'"
        )
