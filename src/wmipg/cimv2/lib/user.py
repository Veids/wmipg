from datetime import datetime, timedelta
from wmipg.common import WMIConnector


class User:
    wmi: WMIConnector

    def __init__(self, wmi_connector: WMIConnector):
        self.wmi = wmi_connector

    def local_users(self):
        return self.wmi.get_class_instances_raw(
            "Select Caption,LocalAccount,SID,Disabled,Lockout FROM Win32_UserAccount"
        )

    def loggedon(self):
        return self.wmi.get_class_instances_raw("Select * From Win32_LoggedOnUser")

    def logon_history(self, login: str = "", days: int = 0):
        request = [
            "Select TimeGenerated,InsertionStrings FROM Win32_NTLogEvent WHERE Logfile='Security' AND EventCode='4624'"
        ]

        if days != 0:
            timeGenerated = datetime.now() - timedelta(days=days)
            timeGenerated = timeGenerated.strftime("%Y%m%d%H%M%S.000000-000")

            request.append(f"AND TimeGenerated > '{timeGenerated}'")

        if login is not None:
            request.append(f"AND Message LIKE '%{login}%'")

        return self.wmi.get_class_instances_raw(" ".join(request))

    def profiles(self):
        return self.wmi.get_class_instances_raw(
            "Select SID,LocalPath,Special,LastUseTime from Win32_UserProfile"
        )
