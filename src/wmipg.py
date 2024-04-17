#!/usr/bin/env python
# Impacket - Collection of Python classes for working with network protocols.
#
# Copyright (C) 2022 Fortra. All rights reserved.
#
# This software is provided under a slightly modified version
# of the Apache Software License. See the accompanying LICENSE file
# for more information.

from __future__ import division
from __future__ import print_function
import sys
import cmd2
import argparse
import logging

from cmd2 import Cmd2ArgumentParser
from impacket.examples import logger
from impacket.examples.utils import parse_target
from impacket import version
from impacket.dcerpc.v5.dcomrt import DCOMConnection, COMVERSION
from impacket.dcerpc.v5.dcom import wmi
from impacket.dcerpc.v5.dtypes import NULL
from impacket.krb5.keytab import Keytab
from rich import print

from src.namespaces.root_cimv2 import CIMv2
from src.namespaces.root_standardcimv2 import StandardCimv2
from src.namespaces.root_securitycenter2 import SecurityCenter2
import src.common as common
from src.common import log, print_data


class WMIConnector:
    def __init__(self, iWbemLevel1Login):
        self.iWbemLevel1Login = iWbemLevel1Login

    def login(self, namespace):
        self.iWbemServices = self.iWbemLevel1Login.NTLMLogin(namespace, NULL, NULL)
        self.iWbemLevel1Login.RemRelease()

    def get_class_instances_raw(self, query, limit = None):
        iEnumWbemClassObject = self.iWbemServices.ExecQuery(query)

        managementObjects = []
        i = 0
        while True:
            try:
                managementObject = iEnumWbemClassObject.Next(0xffffffff, 1)[0]
                managementObjects.append(managementObject)
            except Exception:
                break

            i += 1
            if limit and i >= limit:
                break

        return managementObjects

    def get_class_instances(self, className, properties = None, where = None):
        if properties is None:
            properties = "*"
        else:
            properties = ",".join(properties)

        where = "" if (where is None or where == "") else f"WHERE {where}"

        query = f"SELECT {properties} FROM {className} {where}"

        return self.get_class_instances_raw(query)

    @staticmethod
    def checkiWbemResponse(banner, resp):
        call_status = resp.GetCallStatus(0) & 0xffffffff
        if call_status != 0:
            from impacket.dcerpc.v5.dcom.wmi import WBEMSTATUS
            try:
                error_name = WBEMSTATUS.enumItems(call_status).name
            except ValueError:
                error_name = 'Unknown'
            log.error('%s - %s (0x%08x)' % (banner, error_name, call_status))
            return resp
        else:
            log.info(f"{banner} - OK")
        return resp


class WMIPG(cmd2.Cmd):
    def __init__(self, *args, **kwargs):
        super().__init__(*args[1:], auto_load_commands=False, **kwargs)

        self.prompt = "WMIPG> "
        self.default_category = "cmd2 Built-in Commands"

        self.connector = WMIConnector(args[0])
        self.command_sets = [
            CIMv2(self.connector),
            StandardCimv2(self.connector),
            SecurityCenter2(self.connector)
        ]
        self.active_sets = []

    def _complete_list_value(self):
        items = []
        for x in self.command_sets:
            items.extend(x.paths)
        return items

    login_parser = Cmd2ArgumentParser(description="Connect to the target namespace")
    login_parser.add_argument("namespace", choices_provider = _complete_list_value)

    @cmd2.with_category('WMI')
    @cmd2.with_argparser(login_parser)
    def do_login(self, ns: argparse.Namespace):
        for x in self.active_sets:
            self.unregister_command_set(x)

        self.connector.login(ns.namespace)
        for x in self.command_sets:
            if ns.namespace.lower() in x.paths:
                print("[+] Loaded %s handler" % x.__class__.__name__)
                self.active_sets.append(x)
                self.register_command_set(x)

    @cmd2.with_category('WMI')
    def do_pg(self, _):
        """Start interactive play ground (IPython)"""

        print('Usage e.g.: self.connector.iWbemServices.ExecQuery("Select Name,SessionId,ProcessId,ParentProcessId,CommandLine from win32_Process")')
        print('            or self.connector.get_class_instances_raw("Select Name,SessionId,ProcessId,ParentProcessId,CommandLine from win32_Process")')
        print('            or common.print_data(self.connector.get_class_instances_raw("Select Name,SessionId,ProcessId,ParentProcessId,CommandLine from win32_Process"))')
        from IPython import embed
        embed()

    query_parser = Cmd2ArgumentParser(description="Perform a raw query")
    query_parser.add_argument("-l", "--list", action="store_true", help = "Output as a list of k: v")
    query_parser.add_argument("query", type = str, help = "Raw query")

    @cmd2.with_category('WMI')
    @cmd2.with_argparser(query_parser)
    def do_query(self, ns: argparse.Namespace):
        print_data(
            self.connector.get_class_instances_raw(
                ns.query
            ),
            style = "list" if ns.list else "table"
        )


def _main(
    address,
    username='',
    password='',
    domain='',
    hashes=None,
    aesKey=None,
    noOutput=False,
    doKerberos=False,
    kdcHost=None,
    cmds = None
):
    lmhash = ''
    nthash = ''
    if hashes is not None:
        lmhash, nthash = hashes.split(':')

    dcom = DCOMConnection(
        address,
        username,
        password,
        domain,
        lmhash,
        nthash,
        aesKey,
        oxidResolver = True,
        doKerberos = doKerberos,
        kdcHost = kdcHost
    )

    try:
        iInterface = dcom.CoCreateInstanceEx(wmi.CLSID_WbemLevel1Login, wmi.IID_IWbemLevel1Login)
        iWbemLevel1Login = wmi.IWbemLevel1Login(iInterface)

        app = WMIPG(
            iWbemLevel1Login,
            allow_cli_args=False
        )

        if cmds:
            for x in cmds:
                app.onecmd(x)
        else:
            app.cmdloop()
    except (Exception, KeyboardInterrupt) as e:
        if logging.getLogger().level == logging.DEBUG:
            import traceback
            traceback.print_exc()
        logging.error(str(e))
        dcom.disconnect()
        sys.stdout.flush()
        sys.exit(1)

    dcom.disconnect()


def main():
    print(version.BANNER)

    parser = argparse.ArgumentParser(add_help=True, description="Executes a semi-interactive shell using Windows "
                                                                "Management Instrumentation.")
    parser.add_argument('target', action='store', help='[[domain/]username[:password]@]<targetName or address>')
    parser.add_argument('-ts', action='store_true', help='Adds timestamp to every logging output')
    parser.add_argument('-debug', action='store_true', help='Turn DEBUG output ON')
    parser.add_argument('-com-version', action='store', metavar="MAJOR_VERSION:MINOR_VERSION",
                        help='DCOM version, format is MAJOR_VERSION:MINOR_VERSION e.g. 5.7')

    group = parser.add_argument_group('authentication')

    group.add_argument('-hashes', action="store", metavar="LMHASH:NTHASH", help='NTLM hashes, format is LMHASH:NTHASH')
    group.add_argument('-no-pass', action="store_true", help='don\'t ask for password (useful for -k)')
    group.add_argument('-k', action="store_true",
                       help='Use Kerberos authentication. Grabs credentials from ccache file '
                            '(KRB5CCNAME) based on target parameters. If valid credentials cannot be found, it will use the '
                            'ones specified in the command line')
    group.add_argument('-aesKey', action="store", metavar="hex key", help='AES key to use for Kerberos Authentication '
                                                                          '(128 or 256 bits)')
    group.add_argument('-dc-ip', action='store', metavar="ip address", help='IP Address of the domain controller. If '
                                                                            'ommited it use the domain part (FQDN) specified in the target parameter')
    group.add_argument('-keytab', action="store", help='Read keys for SPN from keytab file')

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    options = parser.parse_args()

    # Init the example's logger theme
    logger.init(options.ts)

    if options.debug is True:
        logging.getLogger().setLevel(logging.DEBUG)
        # Print the Library's installation path
        logging.debug(version.getInstallationPath())
    else:
        logging.getLogger().setLevel(logging.INFO)

    if options.com_version is not None:
        try:
            major_version, minor_version = options.com_version.split('.')
            COMVERSION.set_default_version(int(major_version), int(minor_version))
        except Exception:
            logging.error("Wrong COMVERSION format, use dot separated integers e.g. \"5.7\"")
            sys.exit(1)

    domain, username, password, address = parse_target(options.target)

    try:
        if domain is None:
            domain = ''

        if options.keytab is not None:
            Keytab.loadKeysFromKeytab(options.keytab, username, domain, options)
            options.k = True

        if password == '' and username != '' and options.hashes is None and options.no_pass is False and options.aesKey is None:
            from getpass import getpass

            password = getpass("Password:")

        if options.aesKey is not None:
            options.k = True

        _main(
            address,
            username,
            password,
            domain,
            options.hashes,
            options.aesKey,
            options.k,
            options.dc_ip,
        )
    except KeyboardInterrupt as e:
        logging.error(str(e))
    except Exception as e:
        if logging.getLogger().level == logging.DEBUG:
            import traceback

            traceback.print_exc()
        logging.error(str(e))
        sys.exit(1)

    sys.exit(0)

if __name__ == '__main__':
    main()
