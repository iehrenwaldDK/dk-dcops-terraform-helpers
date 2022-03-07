#!/usr/bin/env python3
import argparse
import logging
import os
import socket
import subprocess
import time
from random import randint
import tempfile
from time import sleep
import logicmonitor_sdk
from logicmonitor_sdk.rest import ApiException

logger = logging.getLogger(__name__)

# A hacky way to find the IP address of the NIC used for default route
def get_dflt_ipaddr(test_addr: str = '8.8.8.8', test_port: int = 80) -> str:
    my_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    my_sock.connect((test_addr, test_port)) # connect() wants a pair

    return my_sock.getsockname()[0]

# Get collector by ID
def gcbi(c_id: int, r_fields: str = '') -> logicmonitor_sdk.models.collector.Collector:
    response = {}
    logger.info('Searching for collector with ID %s', c_id)

    try:
        response = lm_api.get_collector_by_id(id=c_id, fields=r_fields)
    except ApiException as e:
        logger.error('  LM API Exception: get_collector_by_id(): %s', e)
        response = {}

    if response and response.id == c_id:
        logger.info('  SUCCESS: %s == %s', c_id, response.hostname)
    else:
        logger.error('  FAILED: Could not find %s', c_id)

    return response

# Get collector group by ID
def gcgbi(cg_id: int, r_fields: str = '') -> logicmonitor_sdk.models.collector_group.CollectorGroup:
    response = {}
    logger.info('Searching for collector group with ID %s', cg_id)

    try:
        response = lm_api.get_collector_group_by_id(id=cg_id, fields=r_fields)
    except ApiException as e:
        logger.error('  LM API Exception: get_collector_group_by_id(): %s', e)
        response = {}

    if response and response.id == cg_id and response.name:
        logger.info('  SUCCESS: %s == %s', cg_id, response.name)
    else:
        logger.error('  FAILED: Could not find %s', cg_id)

    return response

# Get collector group by name
def gcgbn(cg_name: str, r_fields: str = '') -> logicmonitor_sdk.models.collector_group.CollectorGroup:
    response = {}
    logger.info('Searching for collector group named %s', cg_name)

    try:
        r_filter   = 'name:"' + cg_name + '"'
        response = lm_api.get_collector_group_list(filter=r_filter, fields=r_fields)
    except ApiException as e:
        logger.error('  LM API Exception: get_collector_group_list(): %s', e)
        response = {}

    if response and response.total == 1 and response.items and response.items[0].name == cg_name:
        logger.info('  SUCCESS: %s == %s', cg_name, response.items[0].id)
        response = gcgbi(cg_id=response.items[0].id)
    else:
        logger.error('  FAILURE: Could not find %s', cg_name)
        response = {}

    return response

# Get collectors in collector group by collector group ID
def gcicg(cg_id: int, r_fields: str = '', r_filter: str = '') -> logicmonitor_sdk.models.collector_pagination_response.CollectorPaginationResponse:
    response = {}
    logger.info('Searching for collectors in collector group with ID %s', cg_id)

    try:
        r_fields = 'id,backupAgentId,enableFailBack,enableFailOverOnCollectorDevice,description'
        r_filter = 'collectorGroupId:"' + str(cg_id) + '"'
        response = lm_api.get_collector_list(fields=r_fields, filter=r_filter)
    except ApiException as e:
        logger.error('  LM API Exception: get_collector_list(): %s', e)
        response = {}

    if response and response.total >= 1:
        logger.info('  SUCCESS: Found collectors in group with ID "%s": ', cg_id)
        for i in response.items:
            logger.info('    %s', i.id)
    else:
        logger.error('  FAILURE: Could not find collectors in group with ID %s', cg_id)
        response = {}

    return response

# Get device/resource by ID
def gdbi(d_id: int, r_fields: str = '') -> logicmonitor_sdk.models.device.Device:
    response = {}
    logger.info('Searching for device with ID %s', d_id)

    try:
        response = lm_api.get_device_by_id(id=d_id, fields=r_fields)
    except ApiException as e:
        logger.error('  LM API Exception: get_device_by_id(): %s', e)
        response = {}

    if response and response.id == d_id and response.display_name:
        logger.info('  SUCCESS: %s == %s', response.id, response.display_name)
    else:
        logger.error('  FAILURE: Could not find device with ID %s', d_id)

    return response

# Get device group by name
def gdgbn(dg_name: str, r_fields: str = '') -> logicmonitor_sdk.models.device_group_pagination_response.DeviceGroupPaginationResponse:
    response = {}
    logger.info('Searching for device group named %s', dg_name)

    try:
        r_filter = 'fullPath:"' + dg_name + '"'
        response = lm_api.get_device_group_list(filter=r_filter, fields=r_fields, size=1)
    except ApiException as e:
        logger.error('  LM API Exception: get_device_group_list(): %s', e)
        response = {}

    if response and response.total == 1 and response.items and response.items[0].full_path == dg_name:
        logger.info('  SUCCESS: %s == %s', dg_name, response.items[0].id)
    else:
        logger.error('  FAILURE: Could not find device group named %s', dg_name)
        response = {}

    return response

# Get escalation chain by name
def gecbn(ec_name: str, r_fields: str = '') -> logicmonitor_sdk.models.escalation_chain_pagination_response.EscalationChainPaginationResponse:
    response = {}
    logger.info('Searching for escalation chain named %s', ec_name)

    try:
        r_filter = 'name:"' + ec_name + '"'
        response = lm_api.get_escalation_chain_list(filter=r_filter, fields=r_fields)
    except ApiException as e:
        logger.error('  LM API Exception: get_escalation_chain_list(): %s', e)
        response = {}

    if response and response.total == 1 and response.items and response.items[0].name == ec_name:
        logger.info('  SUCCESS: %s == %s', ec_name, response.items[0].id)
    else:
        logger.error('  FAILURE: Could not find escalation chain named %s', ec_name)
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
    logger.info('Patching device with ID %s via method %s', d_id, patch_type)

    gdbi_response = gdbi(d_id)
    if gdbi_response.id:
        try:
            response = lm_api.patch_device(id=d_id, body=payload, op_type=patch_type)
        except ApiException as e:
            logger.error('  LM API Exception: patch_device(): %s', e)
    else:
        logger.error('  FAILURE: Error in gdbi() response.  Dump: %s', gdbi_response)

    if response and response.id:
        logger.info('  SUCCESS: Patched device ID %s with new data', d_id)
        is_success = True
    else:
        logger.error('  FAILURE: Could not patch device ID %s.  Dump: %s', d_id, response)

    return is_success

# Patch collector by ID
def pcbi(c_id: int, payload: dict) -> bool:
    is_success = False
    response = {}

    logger.info('Patching collector with ID %s', c_id)
    gcbi_response = gcbi(c_id)
    if gcbi_response.id:
        try:
            response = lm_api.patch_collector_by_id(id=c_id, body=payload)
        except ApiException as e:
            logger.error('  LM API Exception: patch_collector_by_id(): %s', e)
    else:
        logger.error('  FAILURE: Error in gcbi() response.  Dump: %s', gcbi_response)

    if response and response.id:
        logger.info('  SUCCESS: Patched collector ID %s with new data', c_id)
        is_success = True
    else:
        logger.error('  FAILURE: Could not patch collector ID %s.  Dump: %s', c_id, response)

    return is_success

# Patch collector group by ID
def pcgbi(cg_id: int, payload: dict) -> bool:
    is_success = False
    response = {}
    logger.info('Patching collector group with ID %s', cg_id)

    gcgbi_response = gcgbi(cg_id)
    if gcgbi_response.id:
        try:
            response = lm_api.patch_collector_group_by_id(id=cg_id, body=payload)
        except ApiException as e:
            logger.error('  LM API Exception: patch_collector_group_by_id(): %s', e)
    else:
        logger.error('  FAILURE: Error in gcgbi() response.  Dump: %s', gcgbi_response)

    if response and response.id:
        logger.info('  SUCCESS: Patched collector group id %s with new data', cg_id)
        is_success = True
    else:
        logger.error('  FAILURE: Could not patch collector group ID %s.  Dump: %s', cg_id, response)

    return is_success

# Download collector installer by ID
def get_collector_installer(c_id: str, os_arch: str, size: str, use_ea: bool) -> str:
    is_success = False
    logger.info('Downloading collector installer with ID %s', c_id)

    gcbi_response = gcbi(c_id)
    if gcbi_response and gcbi_response.id:
        try:
            response = lm_api.get_collector_installer(collector_id=c_id, os_and_arch=os_arch,
                collector_size=size, use_ea=use_ea)
        except ApiException as e:
            logger.error('  LM API Exception: get_collector_installer(): %s', e)
            response = {}

        if response and response.status == 200:
            logger.info('  Beginning download')
            dl_start_time = time.time()
            with tempfile.NamedTemporaryFile(delete=False) as installer:
                installer.write(response.data)
                installer.flush()
                installer.close()
            dl_time = round((time.time() - dl_start_time), 2)
            logger.info('  SUCCESS: Downloaded collector installer in %s seconds', dl_time)
            is_success = True
        else:
            logger.error('  FAILURE: Remote end sent non-OK response code (%s)', response.status)
    else:
        logger.info('  FAILURE: Error in gcbi() response.  Dump: %s', gcbi_response)

    return installer.name if is_success else None

# Run installer
def run_collector_installer(filename: str) -> bool:
    is_success = False
    logger.info('Running collector installer from %s', filename)

    if os.path.exists(filename):
        os.chmod(filename, 0o755)
        runner = subprocess.run([filename, '-y', '-m'])
        if runner.returncode == 0:
            logger.info('  SUCCESS: Installer exited successfully')
            is_success = True
        else:
            logger.error('  FAILURE: Installer exited with non-zero return code (%s)', runner.returncode)
    else:
        logger.error('  FAILURE: Could not access %s', filename)

    return is_success

# Set collector escalation chain
def set_collector_esc_chain(c_id: int, ec_name: str) -> bool:
    is_success = False
    logger.info('Setting escalation chain on collector ID %s to %s', c_id, ec_name)

    gcbi_response = gcbi(c_id)
    if gcbi_response:
        gecbn_response = gecbn(ec_name)
    else:
        logger.error('  FAILURE: Error in gcbi() response.  Dump: %s', gcbi_response)

    if gcbi_response and gcbi_response.id and gecbn_response and gecbn_response.total == 1:
        updated_data = gcbi_response
        updated_data.escalating_chain_id = gecbn_response.items[0].id

        if pcbi(c_id, updated_data):
            logger.info('  SUCCESS')
            is_success = True
        else:
            logger.error('  FAILURE')
    else:
        logger.error('  FAILURE: Error in gcbi() or gecbn() response.  Dumps: %s, %s', gcbi_response, gecbn_response)

    return is_success

# Set collector device name
def set_collector_dev_name(c_id: int, display_name: str, ipaddr: str = '') -> bool:
    is_success = False
    logger.info('Setting device name on collector ID %s', c_id)

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
                logger.info('  SUCCESS: Set display name to %s and IP address to %s', collector_dn, collector_ip)
                is_success = True
            else:
                logger.error('  FAILURE: Could not set display name and/or IP address')
        else:
            logger.error('  FAILURE: Error in gdbi() response.  Dump: %s', gdbi_response)
    else:
        logger.error('  FAILURE: Error in gcbi() response.  Dump: %s', gcbi_response)

    return is_success

# Set custom properties of a collector device resource, mostly used for SNMPv3
def set_collector_dev_cp(c_id: int, ncp: list) -> bool:
    is_success = False
    logger.info('Setting custom properties for device ID %s', c_id)

    gcbi_response = gcbi(c_id, r_fields='id,hostname,collectorDeviceId')
    if gcbi_response and gcbi_response.id and gcbi_response.collector_device_id != 0:
        gdbi_response = gdbi(d_id=gcbi_response.collector_device_id)
        if gdbi_response and gdbi_response.id:
            updated_data = gdbi_response
            updated_data.custom_properties = ncp

            if pdbi(gdbi_response.id, updated_data):
                logger.info('  SUCCESS')
                is_success = True
            else:
                logger.error('  FAILURE')
        else:
            logger.error('  FAILURE: Error in gdbi() response.  Dump: %s', gdbi_response)
    else:
        logger.error('  FAILURE: error in gcbi() response.  Dump: %s', gcbi_response)

    return is_success

# Set collector group auto-balance
def set_collector_grp_ab(cg_id: int, ab_state: str, ab_threshold: int = '10000') -> bool:
    is_success = False
    logger.info('Setting auto-balance to %s on collector group ID %s', ab_state, cg_id)

    gcgbi_response = gcgbi(cg_id)
    if gcgbi_response and gcgbi_response.id == cg_id:
        new_ab_state = 'true' if ab_state == 'enable' else 'false'

        updated_data = gcgbi_response
        updated_data.auto_balance = new_ab_state
        updated_data.auto_balance_instance_count_threshold = ab_threshold

        if pcgbi(cg_id, updated_data):
            logger.info('  SUCCESS')
            is_success = True
        else:
            logger.error('  FAILURE')
    else:
        logger.error('  FAILURe: Error in gcgbi() response.  Dump: %s', gcgbi_response)

    return is_success

# Set collector group failover
def set_collector_grp_fo(cg_id: str, fo_state: str, no_sleep: bool) -> bool:
    is_success = False
    tripped = False
    logger.info('Setting failover to %s on collector group ID %s', fo_state, cg_id)

    # Why are we sleeping a random time?  So we give all collectors a chance
    #  to download/install/configure/verify.  It's safe for this to run on
    #  all collectors.
    if not no_sleep:
        sleep_min = 120
        sleep_max = 300
        sleep_time = randint(sleep_min, sleep_max)
        logger.info('  Sleeping %s seconds to allow all collectors to come up', sleep_time)
        sleep(sleep_time)

    gcgbi_response = gcgbi(cg_id)
    if gcgbi_response and gcgbi_response.id and gcgbi_response.id == cg_id:
        gcicg_response = gcicg(cg_id)
        if gcicg_response and gcicg_response.items:
            if gcicg_response.total < 2:
                logger.error('  FAILURE: Not enough collectors to enable failover (%s)', gcicg_response.total)
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
                        logger.info('  SUCCESS: %s -> %s', updated_data[index].id, updated_data[index].backup_agent_id)
                    else:
                        logger.info('  FAILURE: %s -> %s', updated_data[index].id, updated_data[index].backup_agent_id)
                        tripped = True

                if not tripped:
                    is_success = True
        else:
            logger.error('  FAILURE: Error in gcicg() response.  Dump: %s', gcicg_response)
    else:
        logger.error('FAILURE: Error in gcgbi() response.  Dump: %s', gcgbi_response)

    return is_success

# Add a collector device to a resource group by resource group ID
def set_collector_dev_grp(c_id: int, dg_id: int) -> bool:
    is_success = False
    logger.info('Adding collector ID %s to device group %s', c_id, dg_id)

    gcbi_response = gcbi(c_id)
    if gcbi_response and gcbi_response.id and gcbi_response.collector_device_id:
        gdbi_response = gdbi(gcbi_response.collector_device_id)
        if gdbi_response and gdbi_response.id and gdbi_response.display_name:
            updated_data = gdbi_response
            new_hg_set = set((gdbi_response.host_group_ids + ',' + str(dg_id)).split(','))
            new_hg = ",".join(new_hg_set)
            updated_data.host_group_ids = new_hg

            if pdbi(gdbi_response.id, updated_data):
                logger.info('  SUCCESS: %s', new_hg_set)
                is_success = True
            else:
                logger.info('  FAILURE: %s', new_hg_set)
        else:
            logger.error('  FAILURE: Error in gdbi() response.  Dump: %s', gdbi_response)
    else:
        logger.error('  FAILURE: Error in gcbi() response.  Dump: %s', gcbi_response)

    return is_success


def main():
    global lm_api
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    # Usual arguments which are applicable for the whole script / top-level args
    parser.add_argument('--portal', required=True, type=str, help='LM Portal Name')
    parser.add_argument('--access-id', required=True, type=str, help='LM API ID')
    parser.add_argument('--access-key',  required=True, type=str, help='LM API Key')
    parser.add_argument('--log-file', required=False, type=str, nargs='?',
        default='/tmp/lm-collector-install-setup.log', help='Write to this log file')
    parser.add_argument('--log-level', required=False, type=str, nargs='?',
        choices=['DEBUG','INFO','WARNING','ERROR','CRITICAL'], default='INFO',
        help='Log level, default is INFO')

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
    parser_devgrp.add_argument('--dg-id', required=False, type=int,
        help='Device Group ID')
    parser_devgrp.add_argument('--dg-name', required=False, type=str,
        help='Path to folder to place collector resource in.  Eg: "/B2C/DCOps/AZDC01/Collectors".  Overrides --dg-id')

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

    numeric_loglevel = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_loglevel, int):
        raise ValueError('Invalid log level: %s' % args.loglevel)
    log_format = "[%(asctime)s %(filename)s:%(lineno)s - %(levelname)s - %(funcName)20s()] %(message)s"
    logging.basicConfig(filename=args.log_file, filemode='a', format=log_format, level=numeric_loglevel)

    logger.info('----------------')
    logger.info('Starting script')
    for arg in vars(args):
        logger.debug('Arg %s: %s', arg, getattr(args, arg))

    lmsdk_cfg = logicmonitor_sdk.Configuration()
    lmsdk_cfg.company = args.portal
    lmsdk_cfg.access_id  = args.access_id
    lmsdk_cfg.access_key = args.access_key
    lm_api = logicmonitor_sdk.LMApi(logicmonitor_sdk.ApiClient(lmsdk_cfg))

    # Download and optionally install the collector
    if args.action == 'install':
        lmc_bin_name = get_collector_installer(args.collector_id, args.os_arch, args.size, args.use_ea)
        if args.dl_only:
            logger.info('  Requested download-only, file is at %s', lmc_bin_name)
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
        if not args.dg_id and not args.dg_name:
            print('Need to specify either --dg-id or --dg-name, not both')
            os._exit(1)

        if args.dg_name:
            gdgbn_response = gdgbn(args.dg_name)
            if gdgbn_response and gdgbn_response.items and gdgbn_response.items[0].id:
                resolved_dgid = gdgbn_response.items[0].id
            else:
                print(f'Cannot resolve {args.dg_name} to a device group id')
                os._exit(1)
        else:
            resolved_dgid = args.dg_id

        if resolved_dgid:
            set_collector_dev_grp(args.collector_id, resolved_dgid)
        else:
            print('Either device group ID or name was invalid')
            os._exit(1)
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
