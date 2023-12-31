import logging

from datetime import datetime
from rich.table import Table
from rich.console import Console
from rich.logging import RichHandler

console = Console()
log = logging.getLogger(__name__)
log.addHandler(RichHandler())
log.propagate = False


def columnFormatter(prop, obj, customFormatter = None):
    value = prop['value']
    if value is None:
        return str(value)

    if prop['stype'] == 'datetime':
        try:
            return str(datetime.strptime(value.split('.')[0], "%Y%m%d%H%M%S"))
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


def print_data(managementObjects, style = "table", customFormatter = None, columns = None):
    if len(managementObjects):
        if style == "table":
            title = managementObjects[0].getClassName()
            headers = list(managementObjects[0].getProperties().keys())
            if columns:
                headers = list(filter(lambda x: x in columns, headers))

            table = Table(title = title)
            for column in headers:
                table.add_column(column, no_wrap=False)

            for obj in managementObjects:
                if not columns:
                    props = [columnFormatter(prop, obj, customFormatter) for prop in obj.getProperties().values()]
                else:
                    props = [columnFormatter(prop, obj, customFormatter) for k, prop in obj.getProperties().items() if k in columns]
                table.add_row(*props)

            console.print(table)
        else:
            for obj in managementObjects:
                header = f"===== {obj.getClassName()} ====="
                console.print(header)
                for k, v in obj.getProperties().items():
                    console.print("%s - %s" % (k, columnFormatter(v, obj, customFormatter)))
                console.print("=" * len(header))
    else:
        log.info("Empty response")
