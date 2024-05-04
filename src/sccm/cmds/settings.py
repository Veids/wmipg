import argparse
import cmd2

from cmd2 import with_default_category

from sccm.lib import Settings
from common import WMIConnector


@with_default_category("SCCM")
class SettingsCMD(cmd2.CommandSet):
    def __init__(self, wmi_connector: WMIConnector):
        super().__init__()
        self.settings = Settings(wmi_connector)

    get_site_push_settings_parser = cmd2.Cmd2ArgumentParser()

    @cmd2.as_subcommand_to("get", "site-push-settings", get_site_push_settings_parser)
    def get_site_push_settings(self, _: argparse.Namespace):
        self.settings.show_site_push_settings()
