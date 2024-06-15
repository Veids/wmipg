import logging

from impacket.dcerpc.v5.dtypes import NULL
from ruamel.yaml import YAML
from importlib.resources import files

from datetime import datetime
from rich.table import Table
from rich.console import Console
from rich.logging import RichHandler

console = Console()
log = logging.getLogger(__name__)
log.addHandler(RichHandler())
log.propagate = False


def columnFormatter(prop, obj, customFormatter=None):
    value = prop["value"]
    if value is None:
        return str(value)

    if prop["stype"] == "datetime":
        try:
            return str(datetime.strptime(value.split(".")[0], "%Y%m%d%H%M%S"))
        except Exception:
            return str(value)

    if customFormatter:
        res = customFormatter(prop, obj)
        if isinstance(res, str):
            return res
        else:
            return str(res)

    try:
        return str(value)
    except TypeError:
        return "#TYPEERROR#"


def print_data(managementObjects, customFormatter=None, columns=None, style="table"):
    if len(managementObjects):
        if style == "table":
            title = managementObjects[0].getClassName()
            headers = list(managementObjects[0].getProperties().keys())
            if columns:
                headers = list(filter(lambda x: x in columns, headers))

            table = Table(title=title)
            for column in headers:
                table.add_column(column, no_wrap=False)

            for obj in managementObjects:
                if not columns:
                    props = [
                        columnFormatter(prop, obj, customFormatter)
                        for prop in obj.getProperties().values()
                    ]
                else:
                    props = [
                        columnFormatter(prop, obj, customFormatter)
                        for k, prop in obj.getProperties().items()
                        if k in columns
                    ]
                table.add_row(*props)

            console.print(table)
        else:
            for obj in managementObjects:
                header = f"===== {obj.getClassName()} ====="
                console.print(header)
                for k, v in obj.getProperties().items():
                    console.print(
                        "%s - %s" % (k, columnFormatter(v, obj, customFormatter))
                    )
                console.print("=" * len(header))
    else:
        log.info("Empty response")


def load_security_definitions():
    yaml = YAML()
    with open(str(files("wmipg.static").joinpath("security.yaml"))) as f:
        secs = yaml.load(f.read())

    data = {}
    for x in secs:
        data[x['process'].lower()] = x

    return data


class WMIConnector:
    def __init__(self, iWbemLevel1Login):
        self.iWbemLevel1Login = iWbemLevel1Login

    def login(self, namespace):
        self.iWbemServices = self.iWbemLevel1Login.NTLMLogin(namespace, NULL, NULL)
        self.iWbemLevel1Login.RemRelease()

    def get_class_instances_raw(self, query, limit=None):
        iEnumWbemClassObject = self.iWbemServices.ExecQuery(query)

        managementObjects = []
        i = 0
        while True:
            try:
                managementObject = iEnumWbemClassObject.Next(0xFFFFFFFF, 1)[0]
                managementObjects.append(managementObject)
            except Exception:
                break

            i += 1
            if limit and i >= limit:
                break

        return managementObjects

    def get_class_instances(self, className, properties=None, where=None):
        if properties is None:
            properties = "*"
        else:
            properties = ",".join(properties)

        where = "" if (where is None or where == "") else f"WHERE {where}"

        query = f"SELECT {properties} FROM {className} {where}"

        return self.get_class_instances_raw(query)

    @staticmethod
    def checkiWbemResponse(banner, resp):
        call_status = resp.GetCallStatus(0) & 0xFFFFFFFF
        if call_status != 0:
            from impacket.dcerpc.v5.dcom.wmi import WBEMSTATUS

            try:
                error_name = WBEMSTATUS.enumItems(call_status).name
            except ValueError:
                error_name = "Unknown"
            log.error("%s - %s (0x%08x)" % (banner, error_name, call_status))
            return resp
        else:
            log.info(f"{banner} - OK")
        return resp
