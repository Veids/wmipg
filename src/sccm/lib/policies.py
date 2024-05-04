from common import WMIConnector, log


class Policies:
    wmi: WMIConnector

    def __init__(self, wmi_connector):
        self.wmi = wmi_connector

    def update_machine(self, collectionID: str, resourceIDs: int):
        clientOperation, _ = self.wmi.iWbemServices.GetObject("SMS_ClientOperation")
        resp = clientOperation.InitiateClientOperation(8, collectionID, 0, resourceIDs)

        if resp.ReturnValue == 0:
            log.info(f"Operation successfully initiated {resp.OperationID}")
        else:
            log.error(f"Failed to initiate an operation")
        return resp
