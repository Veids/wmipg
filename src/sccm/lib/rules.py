from common import WMIConnector


class Rules:
    wmi: WMIConnector

    def __init__(self, wmi_connector: WMIConnector):
        self.wmi = wmi_connector

    def get(self, _: str):
        return self.wmi.get_class_instances("SMS_Query")
