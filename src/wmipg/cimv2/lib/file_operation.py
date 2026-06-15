import fnmatch

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
        drive, path = self._split_drive_path(path)
        paths = [path]
        if self._has_glob(path):
            paths = self._expand_glob_paths(drive, path)

        directories = []
        files = []
        for path in paths:
            path_directories, path_files = self._list_files_at_path(drive, path)
            directories.extend(path_directories)
            files.extend(path_files)

        return directories, files

    def _list_files_at_path(self, drive: str, path: str) -> tuple[list[str], list[str]]:
        path = self._escape_wql_value(path)

        directories = self.wmi.get_class_instances_raw(
            f"SELECT Caption,CreationDate,LastAccessed,FileSize FROM CIM_Directory Where Drive='{drive}:' and PATH='{path}'"
        )
        files = self.wmi.get_class_instances_raw(
            f"SELECT Caption,CreationDate,LastAccessed,FileSize,Version FROM CIM_DataFile Where Drive='{drive}:' and PATH='{path}'"
        )

        return directories, files

    def _expand_glob_paths(self, drive: str, path: str) -> list[str]:
        parts = [part for part in path.strip("\\").split("\\") if part]
        paths = ["\\"]

        for part in parts:
            if not self._has_glob(part):
                paths = [self._join_directory_path(path, part) for path in paths]
                continue

            matches = []
            for path in paths:
                for directory in self._list_child_directories(drive, path):
                    props = directory.getProperties()
                    file_name = props.get("FileName", {}).get("value")
                    if not file_name:
                        continue
                    if fnmatch.fnmatchcase(file_name.lower(), part.lower()):
                        matches.append(self._join_directory_path(path, file_name))

            paths = matches
            if not paths:
                break

        return paths

    def _list_child_directories(self, drive: str, path: str):
        path = self._escape_wql_value(path)
        return self.wmi.get_class_instances_raw(
            f"SELECT Caption,FileName FROM CIM_Directory Where Drive='{drive}:' and PATH='{path}'"
        )

    @staticmethod
    def _split_drive_path(path: str) -> tuple[str, str]:
        drive, path = path.replace("/", "\\").split(":", 1)
        if not path.startswith("\\"):
            path = f"\\{path}"
        if not path.endswith("\\"):
            path = f"{path}\\"

        return drive, path

    @staticmethod
    def _join_directory_path(path: str, directory: str) -> str:
        if path == "\\":
            return f"\\{directory}\\"

        return f"{path}{directory}\\"

    @staticmethod
    def _has_glob(path: str) -> bool:
        return any(char in path for char in "*?[")

    @staticmethod
    def _escape_wql_value(value: str) -> str:
        return value.replace("\\", r"\\").replace("'", "''")

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
