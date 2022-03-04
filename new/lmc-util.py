#!/usr/bin/env python3
import argparse
import os
import parser
import socket
import subprocess
from random import randint
import tempfile
import time
import logicmonitor_sdk
from logicmonitor_sdk.rest import ApiException

# Show a message and exit
def err_and_die(msg: str) -> None:
    print(msg)
    os._exit(1)

# A hacky way to find the IP address of the NIC used for default route
def get_dflt_ipaddr(test_addr: str = '8.8.8.8', test_port: int = 80) -> str:
    my_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    my_sock.connect((test_addr, test_port)) # connect() wants a pair

    return my_sock.getsockname()[0]

# Get collector by ID
def gcbi(c_id: int, r_fields: str = '') -> logicmonitor_sdk.models.collector.Collector:
    response = {}
    print(f'gcbi(): Searching for collector id {c_id}')

    try:
        response = lm_api.get_collector_by_id(id=c_id, fields=r_fields)
    except ApiException as e:
        print(f'LM API Exception: get_collector_by_id(): {e}')
        response = {}

    if response and response.id == c_id:
        print(f'gcbi(): Found collector id {c_id}')
    else:
        print(f'gcbi(): Did not find collector id {c_id}')

    return response

# Get collector group by ID
def gcgbi(cg_id: int, r_fields: str = '') -> logicmonitor_sdk.models.collector_group.CollectorGroup:
    response = {}
    print(f'gcgbi(): Searching for collector group id {cg_id}')

    try:
        response = lm_api.get_collector_group_by_id(id=cg_id, fields=r_fields)
    except ApiException as e:
        print(f'LM API Exception: get_collector_group_by_id(): {e}')
        response = {}

    if response and response.id == cg_id and response.name:
        print(f'gcgbi(): Found collector group id {cg_id} with name {response.name}')
    else:
        print(f'gcgbi(): Did not find collector group id {cg_id}')

    return response

# Get collector group by name
def gcgbn(cg_name: str, r_fields: str = '') -> logicmonitor_sdk.models.collector_group.CollectorGroup:
    response = {}
    print(f'gcgbn(): Searching for collector group name {cg_name}')

    try:
        r_filter   = 'name:"' + cg_name + '"'
        response = lm_api.get_collector_group_list(filter=r_filter, fields=r_fields)
    except ApiException as e:
        print(f'LM API Exception: get_collector_group_list(): {e}')
        response = {}

    if response and response.total == 1 and response.items and response.items[0].name == cg_name:
        print(f'gcgbn(): Found collector group with name {cg_name} and id {response.items[0].id}')
        response = gcgbi(cg_id=response.items[0].id)
    else:
        print(f'gcgbn(): Did not find collector group with name {cg_name}')
        response = {}

    return response

# Get collectors in collector group by collector group ID
def gcicg(cg_id: int, r_fields: str = '', r_filter: str = '') -> logicmonitor_sdk.models.collector_pagination_response.CollectorPaginationResponse:
    response = {}
    print(f'gcicg(): Searching for collectors in collector group id {cg_id}')

    try:
        r_fields = 'id,backupAgentId,enableFailBack,enableFailOverOnCollectorDevice,description'
        r_filter = 'collectorGroupId:"' + str(cg_id) + '"'
        response = lm_api.get_collector_list(fields=r_fields, filter=r_filter)
    except ApiException as e:
        print(f'LM API Exception: get_collector_list(): {e}')
        response = {}

    if response and response.total >= 1:
        print(f'gcicg(): Found collectors in collector group id {cg_id}: ', end='')
        for i in response.items:
            print(f'{i.id} ', end='')
        print('')
    else:
        print(f'gcicg(): Did not find any collectors in colletor group id {cg_id}')
        response = {}

    return response

# Get device/resource by ID
def gdbi(d_id: int, r_fields: str = '') -> logicmonitor_sdk.models.device.Device:
    response = {}
    print(f'gdbi(): Searching for device with id {d_id}')

    try:
        response = lm_api.get_device_by_id(id=d_id, fields=r_fields)
    except ApiException as e:
        print(f'LM API Exception: get_device_by_id(): {e}')
        response = {}

    if response and response.id == d_id and response.display_name:
        print(f'gdbi(): Found device with id {response.id} named {response.display_name}')
    else:
        print(f'gdbi(): Did not find device with id {d_id}')

    return response

# Get device group by name
def gdgbn(dg_name: str, r_fields: str = '') -> logicmonitor_sdk.models.device_group_pagination_response.DeviceGroupPaginationResponse:
    response = {}
    print(f'gdgbn(): Searching for device group with name {dg_name}')

    try:
        r_filter = 'fullPath:"' + dg_name + '"'
        response = lm_api.get_device_group_list(filter=r_filter, fields=r_fields, size=1)
    except ApiException as e:
        print(f'LM API Exception: get_device_group_list(): {e}')
        response = {}

    if response and response.total == 1 and response.items and response.items[0].full_path == dg_name:
        print(f'gdgbn(): Found device group with name {dg_name} and id {response.items[0].id}')
    else:
        print(f'gdgbn(): Did not find device group with name {dg_name}')
        response = {}

    return response

# Get escalation chain by name
def gecbn(ec_name: str, r_fields: str = '') -> logicmonitor_sdk.models.escalation_chain_pagination_response.EscalationChainPaginationResponse:
    response = {}
    print(f'gecbn(): Searching for escalation chain with name {ec_name}')

    try:
        r_filter = 'name:"' + ec_name + '"'
        response = lm_api.get_escalation_chain_list(filter=r_filter, fields=r_fields)
    except ApiException as e:
        print(f'LM API Exception: get_escalation_chain_list(): {e}')
        response = {}

    if response and response.total == 1 and response.items and response.items[0].name == ec_name:
        print(f'gecbn(): Found escalation chain with name {ec_name} and id {response.items[0].id}')
    else:
        print(f'gecbn(): Did not find escalation chain with name {ec_name}')
        response = {}

    return response

# Patch device by ID
# https://www.logicmonitor.com/support/rest-api-developers-guide/v1/devices/update-a-device#PATCH
#  To add or update just one or a few device properties in the customProperties object, but not all
#  of them, you’ll need to additionally use the opType query parameter. The opType query parameter
#  can be set to add, refresh or replace.
#
#  opType=add indicates that the properties included in the payload will be added, but all existing
#   properties will remain the same.
#  opType=replace indicates that the properties included in the request payload will be added if
#   they don’t already exist, or updated if they do already exist, but all other existing properties
#   will remain the same.
#  opType=refresh indicates that the properties will be replaced with those included in the request
#   payload.
def pdbi(d_id: int, payload: dict, patch_type: str = 'replace') -> bool:
    is_success = False
    response = {}
    print(f'pdbi(): Patching device id {d_id} with method {patch_type}')

    gdbi_response = gdbi(d_id)
    if gdbi_response.id:
        try:
            response = lm_api.patch_device(id=d_id, body=payload, op_type=patch_type)
        except ApiException as e:
            print(f'LM API Exception: patch_device(): {e}')
    else:
        print('pbdi(): Failure in gdbi() response')

    if response and response.id:
        print(f'pdbi(): Successfully patched device id {d_id} with new data')
        is_success = True
    else:
        print(f'pdbi(): Failed to patch device id {d_id} with new data')

    return is_success

# Patch collector by ID
def pcbi(c_id: int, payload: dict) -> bool:
    is_success = False
    response = {}

    gcbi_response = gcbi(c_id)
    if gcbi_response.id:
        try:
            response = lm_api.patch_collector_by_id(id=c_id, body=payload)
        except ApiException as e:
            print(f'LM API Exception: patch_collector_by_id(): {e}')
    else:
        print('pcbi(): Failure in gcbi() response')

    if response and response.id:
        print(f'pcbi(): Successfully patched collector id {c_id} with new data')
        is_success = True
    else:
        print(f'pcbi(): Failed to patch collector id {c_id} with new data')

    return is_success

# Patch collector group by ID
def pcgbi(cg_id: int, payload: dict) -> bool:
    is_success = False
    response = {}
    print(f'pcgbi(): Patching collector group id {cg_id}')

    gcgbi_response = gcgbi(cg_id)
    if gcgbi_response.id:
        try:
            response = lm_api.patch_collector_group_by_id(id=cg_id, body=payload)
        except ApiException as e:
            print(f'LM API Exception: patch_collector_group_by_id(): {e}')
    else:
        print('pcgbi(): Failure in gcgbi() response')

    if response and response.id:
        print(f'pcgbi(): Successfully patched collector group {cg_id} with new data')
        is_success = True
    else:
        print(f'pcgbi(): Failed to patch collector group {cg_id} with new data')

    return is_success

# Download collector installer by ID
def get_collector_installer(c_id: str, os_arch: str, size: str, use_ea: bool) -> str:
    is_success = False
    print(f'get_collector_installer(): c_id={c_id} os_arch={os_arch} size={size} use_ea={use_ea}')

    gcbi_response = gcbi(c_id)
    if gcbi_response and gcbi_response.id:
        try:
            response = lm_api.get_collector_installer(collector_id=c_id, os_and_arch=os_arch,
                collector_size=size, use_ea=use_ea)
        except ApiException as e:
            print(f'LM API Exception: get_collector_installer(): {e}')
            response = {}

        if response and response.status == 200:
            print('get_collector_installer(): Downloading installer')
            dl_start_time = time.time()
            with tempfile.NamedTemporaryFile(delete=False) as installer:
                installer.write(response.data)
                installer.flush()
                installer.close()
            dl_time = round((time.time() - dl_start_time), 2)
            print(f'get_collector_installer(): Finished in {dl_time} seconds')
            is_success = True
        else:
            print(f'get_collector_installer(): Failure in response ({response.status})')
    else:
        print('get_collector_installer(): Failure in gcbi() response')

    return installer.name if is_success else None

# Run installer
def run_collector_installer(filename: str) -> bool:
    is_success = False
    print(f'run_collector_installer(): filename={filename} size={size}')

    if os.path.exists(filename):
        os.chmod(filename, 0o755)
        runner = subprocess.run([filename, '-y', '-m'])
        if runner.returncode == 0:
            print(f'run_collector_installer(): Installer exited successfully')
            is_success = True
        else:
            print(f'run_collector_installer(): Installed exited with non-zero code ({runner.returncode})')
    else:
        print(f'run_collector_installer(): Could not locate {filename}')

    return is_success

# Set collector escalation chain
def set_collector_esc_chain(c_id: int, ec_name: str) -> bool:
    is_success = False
    print(f'set_collector_esc_chain(): c_id={c_id} ec_name={ec_name}')

    gcbi_response = gcbi(c_id)
    if gcbi_response:
        gecbn_response = gecbn(ec_name)
    else:
        print('set_collector_esc_chain(): Failure in gcbi() response')

    if gcbi_response and gcbi_response.id and gecbn_response and gecbn_response.total == 1:
        updated_data = gcbi_response
        updated_data.escalating_chain_id = gecbn_response.items[0].id

        if pcbi(c_id, updated_data):
            print('set_collector_esc_chain(): Success')
            is_success = True
        else:
            print('set_collector_esc_chain(): Failure')
    else:
        print('set_collector_esc_chain(): Failure in gcbi() or gecbn() response')

    return is_success

# Set collector device name
def set_collector_dev_name(c_id: int, display_name: str, ipaddr: str = '') -> bool:
    is_success = False
    print(f'set_collector_dev_name(): c_id={c_id} display_name={display_name} ipaddr={ipaddr}')

    gcbi_response = gcbi(c_id)
    if gcbi_response and gcbi_response.id and gcbi_response.collector_device_id:
        gdbi_response = gdbi(gcbi_response.collector_device_id)
        if gdbi_response and gdbi_response.id and gdbi_response.display_name:
            collector_dn = display_name if display_name else gcbi_response.hostname
            collector_ip = ipaddr if ipaddr else get_dflt_ipaddr()
            updated_data = gdbi_response
            updated_data.name = collector_ip
            updated_data.display_name = collector_dn

            if pdbi(gdbi_response.id, updated_data):
                print('set_collector_dev_name(): Success')
                is_success = True
            else:
                print('set_collector_dev_name(): Failure')
        else:
            print('set_collector_dev_name(): Failure in gdbi() response')
    else:
        print('set_collector_dev_name(): Failure in gcbi() response')

    return is_success

# Set custom properties of a collector device resource, mostly used for SNMPv3
def set_collector_dev_cp(c_id: int, ncp: list) -> bool:
    is_success = False
    print(f'set_collector_dev_cp(): c_id={c_id} ncp={ncp}')

    gcbi_response = gcbi(c_id, r_fields='id,hostname,collectorDeviceId')
    if gcbi_response and gcbi_response.id and gcbi_response.collector_device_id != 0:
        gdbi_response = gdbi(d_id=gcbi_response.collector_device_id)
        if gdbi_response and gdbi_response.id:
            updated_data = gdbi_response
            updated_data.custom_properties = ncp

            if pdbi(gdbi_response.id, updated_data):
                print('set_collector_dev_cp(): Success')
                is_success = True
            else:
                print('set_collector_dev_cp(): Failure')
        else:
            print('set_collector_dev_cp(): Failure in gdbi() response')
    else:
        print('set_collector_dev_cp(): Failure in gcbi() response')

    return is_success

# Set collector group auto-balance
def set_collector_grp_ab(cg_id: int, ab_state: str, ab_threshold: int = '10000') -> bool:
    is_success = False
    print(f'set_collector_grp_ab(): cg_id={cg_id} ab_state={ab_state} ab_threshold={ab_threshold}')

    gcgbi_response = gcgbi(cg_id)
    if gcgbi_response and gcgbi_response.id == cg_id:
        new_ab_state = 'true' if ab_state == 'enable' else 'false'

        updated_data = gcgbi_response
        updated_data.auto_balance = new_ab_state
        updated_data.auto_balance_instance_count_threshold = ab_threshold

        if pcgbi(cg_id, updated_data):
            print('set_collector_grp_ab(): Success')
            is_success = True
        else:
            print('set_collector_grp_ab(): Failure')
    else:
        print('set_collector_grp_ab(): Failure in gcgbi() response')

    return is_success

# Set collector group failover
def set_collector_grp_fo(cg_id: str, fo_state: str, no_sleep: bool) -> bool:
    is_success = False
    tripped = False
    print(f'set_collector_grp_fo(): cg_id={cg_id} fo_state={fo_state} no_sleep={no_sleep}')

    # Why are we sleeping a random time?  So we give all collectors a chance
    #  to download/install/configure/verify.  It's safe for this to run on
    #  all collectors.
    if not no_sleep:
        sleep_min = 120
        sleep_max = 300
        sleep_time = randint(sleep_min, sleep_max)
        print(f'set_collector_group_failover(): Sleeping {sleep_time}s')
        sleep(sleep_time)

    gcgbi_response = gcgbi(cg_id)
    if gcgbi_response and gcgbi_response.id and gcgbi_response.id == cg_id:
        gcicg_response = gcicg(cg_id)
        if gcicg_response and gcicg_response.items:
            if gcicg_response.total < 2:
                print(f'set_collector_grp_fo(): Not enough collectors to enable failover ({gcicg_response.total})')
            else:
                backup_index = 0
                updated_data = gcicg_response.items
                # This is a little tricky
                for index, element in enumerate(updated_data):
                    if index+1 >= gcicg_response.total:
                        backup_index = 0
                    else:
                        backup_index += 1

                    if fo_state == 'enable':
                        updated_data[index].backup_agent_id = gcicg_response.items[backup_index].id
                        updated_data[index].enable_fail_back = True
                        updated_data[index].enable_fail_over_on_collector_device = False
                    else:
                        updated_data[index].backup_agent_id = 0
                        updated_data[index].enable_fail_back = False
                        updated_data[index].enable_fail_over_on_collector_device = False

                    if pcbi(gcicg_response.items[index].id, updated_data[index]):
                        print(f'set_collector_grp_fo(): Success {updated_data[index].id} -> {updated_data[index].backup_agent_id}')
                    else:
                        print(f'set_collector_grp_fo(): Failure {updated_data[index].id} -> {updated_data[index].backup_agent_id}')
                        tripped = True

                if not tripped:
                    is_success = True
        else:
            print('set_collector_grp_fo(): Failure in gcicg() response')
    else:
        print('set_collector_grp_fo(): Failure in gcgbi() response')

    return is_success

# Add a collector device to a resource group
def set_collector_dev_grp(c_id: int, dg_name: str) -> bool:
    is_success = False
    print(f'set_collector_dev_grp(): c_id={c_id} dg_name={dg_name}')

    gdgbn_response = gdgbn(dg_name)
    if gdgbn_response and gdgbn_response.items and gdgbn_response.items[0].full_path == dg_name:
        gcbi_response = gcbi(c_id)
        if gcbi_response and gcbi_response.id and gcbi_response.collector_device_id:
            gdbi_response = gdbi(gcbi_response.collector_device_id)
            if gdbi_response and gdbi_response.id and gdbi_response.display_name:
                updated_data = gdbi_response
                new_hg_set = set((gdbi_response.host_group_ids + ',' + str(gdgbn_response.items[0].id)).split(','))
                new_hg = ",".join(new_hg_set)
                updated_data.host_group_ids = new_hg

                if pdbi(gdbi_response.id, updated_data):
                    print(f'set_collector_dev_grp(): Success {new_hg_set}')
                    is_success = True
                else:
                    print(f'set_collector_dev_grp(): Failure {new_hg_set}')
            else:
                print('set_collector_dev_grp(): Failure in gdbi() response')
        else:
            print('set_collector_dev_grp(): Failure in gcbi() response')
    else:
        print('set_collector_dev_grp(): Failure in gdgbn() response')

    return is_success


def main():
    global lm_api
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    # Usual arguments which are applicable for the whole script / top-level args
    parser.add_argument('--portal', required=True, type=str, help='LM Portal Name')
    parser.add_argument('--access-id', required=True, type=str, help='LM API ID')
    parser.add_argument('--access-key',  required=True, type=str, help='LM API Key')
#    parser.add_argument('--log-file', required=False, type=str, nargs='?',
#        default='/tmp/lm-collector-install-setup.log', help='Write to this log file')
#    parser.add_argument('--log-level', required=False, type=str, nargs='?',
#        choices=['DEBUG','INFO','WARNING','ERROR','CRITICAL'], default='INFO',
#        help='Log level, default is INFO')

    # Same subparsers as usual
    subparsers = parser.add_subparsers(help='Desired action to perform', dest='action')

    # Usual subparsers not using common options
    #parser_other = subparsers.add_parser("extra-action", help='Do something without db')

    # Create parent subparser. Note `add_help=False` and creation via `argparse.`
    parent_parser = argparse.ArgumentParser(add_help=False,formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parent_parser.add_argument('--blah', required=False, type=str, help='testy')
#    parent_parser.add_argument('--portal', required=True, type=str, help='LM Portal Name')
#    parent_parser.add_argument('--access-id', required=True, type=str, help='LM API ID')
#    parent_parser.add_argument('--access-key',  required=True, type=str, help='LM API Key')

    # Subparsers that use the parent
    parser_install = subparsers.add_parser('install', parents=[parent_parser],
        help='Download and install collector',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser_install.add_argument('--collector-id', required=True, type=int,
        help='LM Collector ID')
    parser_install.add_argument('--os-arch', required=False, type=str,
        choices=['Linux64', 'Windows64'], default='Linux64',
        help='OS and Arch string recognized by LM API')
    parser_install.add_argument('--size', required=False, type=str,
        choices=['nano', 'small', 'medium', 'large', 'extra_large', 'double_extra_large'],
        default='medium', help='Collector size')
    parser_install.add_argument('--use-ea', required=False, action='store_true', default=False,
        help='Download early access collector version')
    parser_install.add_argument('--dl-only', required=False, action='store_true', default=False,
        help='Download only, do not install')

    parser_devgrp = subparsers.add_parser('devgrp', parents=[parent_parser],
        help='Add collector VM to a device group',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser_devgrp.add_argument('--collector-id', required=True, type=int,
        help='LM Collector ID')
    parser_devgrp.add_argument('--device-group', required=True, type=str,
        help='Path to folder to place collector resource in.  Eg: "/B2C/DCOps/AZDC01/Collectors"')

    parser_devname = subparsers.add_parser('devname', parents=[parent_parser],
        help='Set collector VM device name',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser_devname.add_argument('--collector-id', required=True, type=int,
        help='LM Collector ID')
    parser_devname.add_argument('--display-name', required=False, type=str,
        help='Override autodetected name text with this')
    parser_devname.add_argument('--ip-address', required=False, type=str,
        help='Override IP addr of collector resource with this')

    parser_echain = subparsers.add_parser('echain', parents=[parent_parser],
        help='Set collector escalation chain',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser_echain.add_argument('--collector-id', required=True, type=int,
        help='LM Collector ID')
    parser_echain.add_argument('--ec-name', required=True, type=str,
        help='Name of Escalation Chain to use if collector is unreachable')

    parser_snmp = subparsers.add_parser('snmp', parents=[parent_parser],
        help='Set collector SNMP custom properties',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser_snmp.add_argument('--collector-id', required=True, type=int,
        help='LM Collector ID')
    parser_snmp.add_argument('--snmp-security', required=False, type=str, default='lm-snmpv3',
        help='SNMPv3 Username')
    parser_snmp.add_argument('--snmp-auth', required=False, type=str, choices=['SHA', 'MD5'],
        default='SHA', help='SNMPv3 Authentication Algorithm')
    parser_snmp.add_argument('--snmp-priv', required=False, type=str, choices=['AES', 'DES'],
        default='AES', help='SNMPv3 Encryption Algorithm')
    parser_snmp.add_argument('--snmp-auth-token', required=True, type=str,
        help='SNMPv3 Authentication Password')
    parser_snmp.add_argument('--snmp-priv-token', required=True, type=str,
         help='SNMPv3 Encrpytion Password')

    parser_cgab = subparsers.add_parser('cgab', parents=[parent_parser],
        help='Set collector group auto balance',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser_cgab.add_argument('--cg-id', required=False, type=int,
        help='LM Collector Group ID')
    parser_cgab.add_argument('--cg-name', required=False, type=str,
        help='Collector Group name instead of id, overrides --cg-id')
    parser_cgab.add_argument('--ab-state', required=True, type=str, choices=['enable', 'disable'],
        default='disable', help='Collector group device resource auto balancing')

    parser_cgfo = subparsers.add_parser('cgfo', parents=[parent_parser],
        help='Set collector group failover',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser_cgfo.add_argument('--cg-id', required=False, type=int,
        help='LM Collector Group ID')
    parser_cgfo.add_argument('--cg-name', required=False, type=str,
        help='Collector Group name instead of id, overrides --cg-id')
    parser_cgfo.add_argument('--fo-state', required=True, type=str, choices=['enable', 'disable'],
        default='enable', help='Collector group device resource monitoring failover')
    parser_cgfo.add_argument('--no-sleep', required=False, action='store_true', default=True,
        help='Do not sleep before executing the failover setup')

    args = parser.parse_args()
#    numeric_loglevel = getattr(logging, args.log_level.upper(), None)    
    print('----------------')
    print('Starting script')
    for arg in vars(args):
#        logger.debug('Arg %s: %s', arg, getattr(args, arg))
        print('    Arg %s: %s' % (arg, getattr(args, arg)))

    lmsdk_cfg = logicmonitor_sdk.Configuration()
    lmsdk_cfg.company = args.portal
    lmsdk_cfg.access_id  = args.access_id
    lmsdk_cfg.access_key = args.access_key
    lm_api = logicmonitor_sdk.LMApi(logicmonitor_sdk.ApiClient(lmsdk_cfg))

    # Download and optionally install the collector
    if args.action == 'install':
        lmc_bin_name = get_collector_installer(args.collector_id, args.os_arch, args.size, args.use_ea)
        if args.dl_only:
            print(f'Requested download-only, file is at {lmc_bin_name}')
        else:
            run_collector_installer(lmc_bin_name)
    # Set the collector resource/device name and IP address
    elif args.action == 'devname':
        set_collector_dev_name(args.collector_id, args.display_name, args.ip_address)
    # Set the SNMPv3 properties on the collector resource/device
    elif args.action == 'snmp':
        snmp_props = [
            {'name': 'snmp.security', 'value': args.snmp_security },
            {'name': 'snmp.auth', 'value': args.snmp_auth },
            {'name': 'snmp.priv', 'value': args.snmp_priv },
            {'name': 'snmp.authToken', 'value': args.snmp_auth_token },
            {'name': 'snmp.privToken', 'value': args.snmp_priv_token },
        ]
        set_collector_dev_cp(args.collector_id, snmp_props)
    # Set the collector-down escalation chain on the collector
    elif args.action == 'echain':
        set_collector_esc_chain(args.collector_id, args.ec_name)
    # Toggle collector group failover
    elif args.action == 'cgfo':
        if not args.cg_id and not args.cg_name:
            print('Need to specify either --cg-id or --cg-name, not both')
            os._exit(1)

        if args.cg_name:
            gcgbn_response = gcgbn(args.cg_name)
            if gcgbn_response and gcgbn_response.id:
                resolved_cgid = gcgbn_response.id
            else:
                print(f'Cannot resolve {args.cg_name} to a collector group id')
                os._exit(1)
        else:
            resolved_cgid = args.cg_id

        if resolved_cgid:
            set_collector_grp_fo(resolved_cgid, args.fo_state, args.no_sleep)
        else:
            print('Either collector group ID or name was invalid')
            os._exit(1)
    elif args.action == 'devgrp':
        set_collector_dev_grp(args.collector_id, args.device_group)
    elif args.action == 'cgab':
        if not args.cg_id and not args.cg_name:
            print('Need to specify either --cg-id or --cg-name, not both')
            os._exit(1)
        if args.cg_name:
            gcgbn_response = gcgbn(args.cg_name)
            if gcgbn_response and gcgbn_response.id:
                resolved_cgid = gcgbn_response.id
            else:
                print(f'Cannot resolve {args.cg_name} to a collector group id')
                os._exit(1)
        else:
            resolved_cgid = args.cg_id

        if resolved_cgid:
            set_collector_grp_ab(resolved_cgid, args.ab_state, 10000)
        else:
            print('Either collector group ID or name was invalid')
            os._exit(1)
    else:
        print('Try --help')

    os._exit(0)

if __name__ == "__main__":
    main()

