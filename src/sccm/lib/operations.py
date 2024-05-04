from typing import Optional
from common import WMIConnector, log


class Operations:
    wmi: WMIConnector

    def __init__(self, wmi_connector: WMIConnector):
        self.wmi = wmi_connector

    def get_status(self, operationID: Optional[int] = None, properties=None):
        whereCond = None
        if operationID:
            whereCond = f"ID={operationID}"

        if properties is None:
            properties = [
                "ID",
                "Type",
                "TotalClients",
                "CompletedClients",
                "FailedClients",
                "State",
                "CollectionID",
            ]

        return self.wmi.get_class_instances(
            "SMS_ClientOperationStatus", properties=properties, where=whereCond
        )

    def remove(self, operationID: int):
        clientOperation, _ = self.wmi.iWbemServices.GetObject("SMS_ClientOperation")
        resp = clientOperation.DeleteClientOperation(operationID)

        if resp.ReturnValue == 0:
            log.info(f"ClientOperation {operationID} successfully removed")
        else:
            log.error(f"Failed to remove ClientOperation {operationID}")
        return resp
