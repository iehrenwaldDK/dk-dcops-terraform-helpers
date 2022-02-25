#!/usr/bin/env python3

import argparse
import logging
import os
import socket
import logicmonitor_sdk
from logicmonitor_sdk.rest import ApiException

def err_and_die(msg):
    logger.critical(msg)
    print(f"Fatal: {msg}")
    os._exit(1)

logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser()
parser.add_argument('--access-id', type=str, help='LM API Access ID', required=True)
parser.add_argument('--access-key', type=str, help='LM API Access Key', required=True)
parser.add_argument('--portal', type=str, help='LM portal/company name', required=True)
parser.add_argument('--collector-id', type=int, help='LM Collector ID to operate on', required=True)
parser.add_argument('--display-name', type=str, help='Override autodetected name with this"', required=False)
parser.add_argument('--ip-address', type=str, help='Override IP address of collector resource with this', required=False)
parser.add_argument('--log-file', type=str, help='Write to this log file', nargs='?', required=False, default='/tmp/lm-collector-install-setup.log')
parser.add_argument('--log-level', type=str, help='Log level [DEBUG|INFO|WARNING|ERROR|CRITICAL], default is INFO', nargs='?', required=False, default='INFO')
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
lmsdk_cfg.access_id = args.access_id
lmsdk_cfg.access_key = args.access_key
lmsdk_cfg.company = args.portal

lm_api = logicmonitor_sdk.LMApi(logicmonitor_sdk.ApiClient(lmsdk_cfg))

# A hacky way to find the IP address of the NIC used for default route
def get_collector_ipaddr():
    my_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    my_sock.connect("8.8.8.8", 80)
    return my_sock.getsockname()[0]

# Search for collector
logger.info('Searching for a collector with id %s', args.collector_id)
try:
    GCBID_fields = 'id,hostname,collectorDeviceId'
    GCBID_response = lm_api.get_collector_by_id(id=args.collector_id, fields=GCBID_fields)
except ApiException as e:
    err_and_die(f'Exception when calling LMApi->get_collector_by_id: {e}')

if not GCBID_response.id:
    err_and_die(f'  Search for collector id {args.collector_id} did not find any results')
else:
    logger.info('  Found %s', GCBID_response.hostname)

# Search for resource/device associated with collector
logger.info('Searching for the associated device with id %s', GCBID_response.collector_device_id)
try:
    GDBID_response = lm_api.get_device_by_id(id=GCBID_response.collector_device_id)
except ApiException as e:
    err_and_die(f'Exception when calling LMApi->get_device_by_id: {e}')

if not GDBID_response.id:
    err_and_die(f'  Search for device {GCBID_response.collector_device_id} did not find any results')
else:
    logger.info('  Found %s', GDBID_response.id)

# Set the display_name to something other than 127.0.0.1_{collectorId}
# Set the name to the IP address of the VM
resolved_cip = args.ip_address if args.ip_address else get_collector_ipaddr()
resolved_cdn = args.display_name if args.display_name else GCBID_response.hostname

logger.info('Setting collector IP address to %s', resolved_cip)
logger.info('Setting collector display name to %s', resolved_cdn)
try:
    updated_data = GDBID_response
    updated_data.name = resolved_cip
    updated_data.display_name = resolved_cdn
    PD_response = lm_api.patch_device(
        id=GCBID_response.collector_device_id,
        body=updated_data)
except ApiException as e:
    print(f"Exception when calling LMApi->patchDevice: {e}\n")

logger.info('Exiting at bottom of script')
os._exit(0)
