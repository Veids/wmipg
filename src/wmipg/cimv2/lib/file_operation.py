from wmipg.common import WMIConnector


class FileOperation:
    wmi: WMIConnector

    def __init__(self, wmi_connector: WMIConnector):
        self.wmi = wmi_connector

    def list_volumes(self):
        return self.wmi.get_class_instances_raw(
            "Select DriveLetter,DeviceID,FileSystem,SystemVolume,Capacity,Label FROM Win32_Volume"
        )

    def list_files(self, path: str) -> tuple[list[str], list[str]]:
        drive, path = path.split(":")
        path = path.replace("\\", r"\\")

        directories = self.wmi.get_class_instances_raw(
            f"SELECT Caption,CreationDate,LastAccessed,FileSize FROM CIM_Directory Where Drive='{drive}:' and PATH='{path}'"
        )
        files = self.wmi.get_class_instances_raw(
            f"SELECT Caption,CreationDate,LastAccessed,FileSize,Version FROM CIM_DataFile Where Drive='{drive}:' and PATH='{path}'"
        )

        return directories, files

    def stat(self, path: str):
        path = path.replace("\\", r"\\")
        obj, _ = self.wmi.iWbemServices.GetObject(f"CIM_DataFile.Name='{path}'")
        return obj

    def mv(self, source: str, dest: str):
        source = source.replace("\\", r"\\")
        dest = dest.replace("\\", r"\\")

        # TIPS: will fail if Name='' contains double quotes
        obj, _ = self.wmi.iWbemServices.GetObject(f"CIM_DataFile.Name='{source}'")
        return obj.Rename(dest)

    def cp(self, source: str, dest: str):
        source = source.replace("\\", r"\\")
        dest = dest.replace("\\", r"\\")

        # TIPS: will fail if Name='' contains double quotes
        obj, _ = self.wmi.iWbemServices.GetObject(f"CIM_DataFile.Name='{source}'")
        return obj.Copy(dest)

    def rm(self, path: str):
        path = path.replace("\\", r"\\")

        # TIPS: will fail if Name='' contains double quotes
        obj, _ = self.wmi.iWbemServices.GetObject(f"CIM_DataFile.Name='{path}'")
        return obj.Delete()
