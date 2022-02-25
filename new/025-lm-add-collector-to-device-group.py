#!/usr/bin/env python3

import argparse
import logging
import os
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
parser.add_argument('--device-group', type=str, help='Path to folder to place collector resource in.  Eg: "/B2C/DCOps/AZDC01/Collectors"', required=True)
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
    err_and_die(f'  Search for device {GCBID_response.collector_device_id} did not return anything')
else:
    logger.info('  Found %s', GDBID_response.id)

# Search for device group to put the resource/device into
logger.info('Searching for a device group at path %s', args.device_group)
try:
    GDGL_filter = 'fullPath:"' + args.device_group +'"'
    GDGL_fields = 'fullPath,id,name'
    GDGL_response = lm_api.get_device_group_list(fields=GDGL_fields, filter=GDGL_filter, size=1)
except ApiException as e:
    err_and_die(f'Exception when calling LMApi->get_device_group_list: {e}')

if not GDGL_response.total or GDGL_response.items[0].full_path != args.device_group:
    err_and_die(f'  Search for device group "{args.device_group}" did not find any results')
else:
    logger.info('  Found group with id %s', GDGL_response.items[0].id)

# Update the resource/device group membership, two different ways to approach
updated_data = GDBID_response
# Add new host group id to the host_group_ids string, splits on comma into list, removes duplicates
new_hg_set = set((GDBID_response.host_group_ids + ',' + str(GDGL_response.items[0].id)).split(','))
new_hg = ",".join(new_hg_set)
updated_data.host_group_ids = new_hg
# This alternative just adds the new host group id to the host_group_ids string.
#updated_data.host_group_ids = GDBID_response.host_group_ids + ',' + str(GDGL_response.items[0].id)

logger.info('Updating device groups for %s to %s', GDBID_response.id, updated_data.host_group_ids)
try:
    PD_response = lm_api.patch_device(id=GDBID_response.id, body=updated_data)
except ApiException as e:
    err_and_die(f'Exception when calling LMApi->patch_device" {e}')

logger.info('Exiting at bottom of script')
os._exit(0)
