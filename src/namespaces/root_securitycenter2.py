import cmd2

from src.common import print_data


@cmd2.with_default_category('WMI')
class SecurityCenter2(cmd2.CommandSet):
    paths = [
        "root/securitycenter2"
    ]

    def __init__(self, connector):
        super().__init__()
        self.connector = connector

    def do_get_av(self, _):
        """Enumerate antivirus software deployed on the system"""

        print_data(
            self.connector.get_class_instances_raw(
                "SELECT * FROM AntivirusProduct"
            )
        )
