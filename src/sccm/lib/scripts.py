import uuid

from base64 import b64encode
from typing import Optional

from common import WMIConnector, log


class Scripts:
    wmi: WMIConnector

    def __init__(self, wmi_connector: WMIConnector):
        self.wmi = wmi_connector

    def get(self, guid: str):
        return self.wmi.iWbemServices.GetObject(f"SMS_Scripts.ScriptGuid='{guid}'")[0]

    def gets(self, properties=None):
        if properties is None:
            properties = [
                "ScriptGuid",
                "ScriptName",
                "ScriptVersion",
                "Author",
                "ScriptType",
                "ApprovalState",
                "Approver",
            ]

        return self.wmi.get_class_instances("SMS_Scripts", properties=properties)

    def get_execution_summary_lazy(self, scriptGuid: Optional[str] = None):
        whereCond = None
        if scriptGuid:
            whereCond = f"ScriptGuid='{scriptGuid}'"

        return self.wmi.get_class_instances(
            "SMS_ScriptsExecutionSummary", properties=None, where=whereCond
        )

    def add(self, scriptName: str, content: str, timeout: int = 60):
        script, _ = self.wmi.iWbemServices.GetObject("SMS_Scripts")
        guid = uuid.uuid4()
        content = b64encode(content.encode("UTF-16")).decode()

        resp = script.CreateScripts(
            str(guid),  # ScriptGuid
            "1",  # ScriptVersion
            scriptName,  # ScriptName
            "",  # ScriptDescription
            "",  # Author
            0,  # ScriptType (0 - PowerShell)
            0,  # ApprovalState (0 - Waiting for approval, 1 - Declined, 3 - Approved)
            "",  # Approver
            "",  # Comment,
            "",  # ParamsDefinition
            "",  # ParameterlistXML,
            content,  # Script (UTF16+b64 encoded)
            timeout,  # Timeout
        )

        if resp.ReturnValue == 0:
            log.info(f"Successfully created script {guid}")
        else:
            log.error(f"Failed to create a script")
        return resp

    def remove(self, scriptGuid: str):
        return self.wmi.checkiWbemResponse(
            f"Removing script {scriptGuid}",
            self.wmi.iWbemServices.DeleteInstanceAsync(
                f"SMS_Scripts.ScriptGuid='{scriptGuid}'"
            ),
        )

    def approve(self, scriptGuid: str):
        obj = self.get(scriptGuid)
        resp = obj.UpdateApprovalState(
            "3",  # ApprovalState (3 - approved),
            "",  # Approver (deprecated)
            "",  # Comment
        )
        obj.RemRelease()

        if resp.ReturnValue == 0:
            log.info(f"Successfully approved script {scriptGuid}")
        else:
            log.error(f"Failed to approve a script")
        return resp

    # creds - https://gist.github.com/Robert-LTH/7423e418aab033d114d7c8a2df99246b
    def run(self, scriptGuid: str, collectionID: str = "", resourceIDs: list[int] = []):
        script = self.get(scriptGuid)
        if script.ApprovalState != 3:
            log.error(
                f"Script {scriptGuid} is not approved, current state: {script.ApprovalState}"
            )
            return None

        param = "<ScriptContent ScriptGuid='{0}'><ScriptVersion>{1}</ScriptVersion><ScriptType>{2}</ScriptType><ScriptHash ScriptHashAlg='SHA256'>{3}</ScriptHash>{4}<ParameterGroupHash ParameterHashAlg='SHA256'></ParameterGroupHash></ScriptContent>".format(
            script.ScriptGuid,
            script.ScriptVersion,
            script.ScriptType,
            script.ScriptHash,
            "<ScriptParameters></ScriptParameters>",
        )
        param = b64encode(param.encode("UTF-8"))

        clientOperation, _ = self.wmi.iWbemServices.GetObject("SMS_ClientOperation")
        resp = clientOperation.InitiateClientOperationEx(
            135,  # Type (Script)
            param,  # Param,
            collectionID,  # TargetCollectionID
            0,  # RandomizationWindow
            resourceIDs,  # TargetResourceIDs
        )

        if resp.ReturnValue == 0:
            log.info(f"Operation successfully initiated {resp.OperationID}")
        else:
            log.error(f"Failed to initiate an operation")

        return resp
