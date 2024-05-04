from datetime import datetime

from typing import List

from common import WMIConnector


class Deployments:
    wmi: WMIConnector

    def __init__(self, wmi_connector):
        self.wmi = wmi_connector

    def add(
        self,
        siteCode,
        applicationName,
        applicationCIID: List[int],
        collectionName,
        collectionID,
    ):
        now = datetime.now().strftime("%Y%m%d%H%M%S.000000+***")

        deployment, _ = self.wmi.iWbemServices.GetObject("SMS_ApplicationAssignment")
        deployment = deployment.SpawnInstance()

        deployment.ApplicationName = applicationName
        deployment.AssignmentName = f"{applicationName}_{collectionID}_Install"
        deployment.AssignmentAction = 2  # Apply
        deployment.AssignmentType = 2  # Application
        deployment.CollectionName = collectionName
        deployment.DesiredConfigType = 1  # Required
        deployment.DisableMOMAlerts = True
        deployment.EnforcementDeadline = now
        deployment.LogComplianceToWinEvent = False
        deployment.NotifyUser = False
        deployment.OfferFlags = 1  # Predeploy
        deployment.OfferTypeID = 0  # Required
        deployment.OverrideServiceWindows = True
        deployment.Priority = 2  # High
        deployment.RebootOutsideOfServiceWindows = False
        deployment.SoftDeadlineEnabled = True
        deployment.SourceSite = siteCode
        deployment.StartTime = now
        deployment.SuppressReboot = 0
        deployment.TargetCollectionID = collectionID
        deployment.UserUIExperience = False  # Do not display user notifications
        deployment.WoLEnabled = False  # Not including this property results in errors displayed in the console
        deployment.AssignedCIs = applicationCIID
        deployment.RequireApproval = False

        return self.wmi.checkiWbemResponse(
            f"Creating new {deployment.AssignmentName} deployment",
            self.wmi.iWbemServices.PutInstance(deployment.marshalMe()),
        )

    def get(self, applicationName=None, collectionID=None, properties=None):
        whereCond = []
        if applicationName:
            whereCond.append(f"ApplicationName='{applicationName}'")

        if collectionID:
            whereCond.append(f"TargetCollectionID='{collectionID}'")

        if len(whereCond):
            whereCond = " and ".join(whereCond)
        else:
            whereCond = None

        if properties is None:
            properties = [
                "ApplicationName",
                "Enabled",
                "CollectionName",
                "TargetCollectionID",
                "NotifyUser",
                "RequireApproval",
                "LastModificationTime",
                "EnforcementDeadline",
                "AssignmentID",
            ]

        return self.wmi.get_class_instances(
            "SMS_ApplicationAssignment", properties=properties, where=whereCond
        )

    def remove(self, assignmentID):
        return self.wmi.checkiWbemResponse(
            f"Removing deployment {assignmentID}",
            self.wmi.iWbemServices.DeleteInstance(
                f"SMS_ApplicationAssignment.AssignmentID={assignmentID}"
            ),
        )
