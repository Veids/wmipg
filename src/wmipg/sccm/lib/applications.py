import uuid
from jinja2 import Environment, FileSystemLoader

from wmipg.common import WMIConnector, log


class Applications:
    wmi: WMIConnector
    env: Environment

    def __init__(self, wmi_connector: WMIConnector):
        self.wmi = wmi_connector
        self.env = Environment(loader=FileSystemLoader("src/sccm/templates/"))

    def add(self, siteId, name, path, runUser, show=False):
        template = self.env.get_template("basic_application.xml")

        scopeId = f"ScopeId_{siteId}"
        appId = f"Application_{uuid.uuid4()}"
        deploymentId = f"DeploymentType_{uuid.uuid4()}"
        fileId = f"File_{uuid.uuid4()}"

        xml = template.render(
            path=path,
            runUser=runUser,
            name=name,
            siteId=siteId,
            scopeId=scopeId,
            appId=appId,
            deploymentId=deploymentId,
            fileId=fileId,
        )

        application, _ = self.wmi.iWbemServices.GetObject("SMS_Application")
        application = application.SpawnInstance()
        application.SDMPackageXML = xml
        application.IsDeployable = True

        if show is False:
            application.IsHidden = True
        else:
            application.IsHidden = False

        return WMIConnector.checkiWbemResponse(
            f"Creating new {name} application",
            self.wmi.iWbemServices.PutInstance(application.marshalMe()),
        )

    def get(self, name=None, properties=None):
        whereCond = f"LocalizedDisplayName='{name}'" if name else None

        if properties is None:
            properties = [
                "CI_ID",
                "LocalizedDisplayName",
                "ExecutionContext",
                "IsEnabled",
                "IsDeployed",
                "IsHidden",
                "CreatedBy",
                "LastModifiedBy",
                "HasContent",
                "DateLastModified",
            ]

        return self.wmi.get_class_instances(
            "SMS_Application", properties=properties, where=whereCond
        )

    def get_xml(self, ciID):
        return self.wmi.iWbemServices.GetObject(f"SMS_Application.CI_ID={ciID}")[
            0
        ].SDMPackageXML

    def remove(self, ciID: str):
        whereCond = f"CI_ID={ciID}"
        applications = self.wmi.get_class_instances(
            "SMS_Application", properties=None, where=whereCond
        )

        if len(applications) == 1:
            application = applications[0]
            resp = application.SetIsExpired(True)
            if resp.ReturnValue == 0:
                log.info(f"Set application {ciID} expired state")
            else:
                log.error(
                    f"Failed to set application {ciID} expired state. Aborting..."
                )
                return None

            return WMIConnector.checkiWbemResponse(
                f"Removing application {ciID}",
                self.wmi.iWbemServices.DeleteInstance(f"SMS_Application.CI_ID={ciID}"),
            )
        else:
            log.error(f"Application {ciID} is not found")
            return None
