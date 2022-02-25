#!/usr/bin/env python3

import argparse
import logging
import os
from random import randint
from time import sleep
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
parser.add_argument('--cg-id', type=int, help='LM Collector ID to add to group', required=True)
parser.add_argument('--really-sleep', action='store_true', required=False, default=False)
#parser.add_argument('--action', type=str, help='Operation to perform', required=True, choices=['enable', 'disable'])
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

# Why are we sleeping a random time?  So we give all collectors a chance
#  to download/install/configure/verify.  It's safe for this to run on
#  all collectors.
SLEEP_MIN = 120
SLEEP_MAX = 300
sleep_time = randint(SLEEP_MIN, SLEEP_MAX)
logger.info('Sleeping %s and then beginning collector failover setup', sleep_time)
if args.really_sleep: sleep(sleep_time)

# Search for collector group
logger.info('Searching for collector group id %s', args.cg_id)
try:
    GCGBID_response = lm_api.get_collector_group_by_id(id=args.cg_id)
except ApiException as e:
    err_and_die(f"Exception when calling LMApi->get_collector_group_by_id: {e}")

if GCGBID_response.id:
    resolved_cgid = GCGBID_response.id
    logger.info('  Found collector group %s', GCGBID_response.name)
else:
    err_and_die('  Did not find a collector group with that id')

# Search for colletors in collector group
logger.info('Searching for collectors in %s', GCGBID_response.name)
try:
    GCL_filter = 'collectorGroupId:"' + str(args.cg_id) + '"'
    GCL_response = lm_api.get_collector_list(
        fields="id,backupAgentId,enableFailBack,enableFailOverOnCollectorDevice",
        filter=GCL_filter)
except ApiException as e:
    err_and_die(f'Exception when calling LMApi->get_collector_list: {e}')

if GCL_response.total == 0:
    err_and_die('  No collectors found in group')
if GCL_response.total < 2:
    err_and_die('  Less than two collectors in group')

MY_INDEX = 0
updated_data = GCL_response.items
# This is a little tricky
for index, element in enumerate(updated_data):
    if index+1 >= GCL_response.total:
        MY_INDEX = 0
    else:
        MY_INDEX += 1

    logger.info('Set %s as backup for %s', GCL_response.items[MY_INDEX].id, updated_data[index].id)
    updated_data[index].backup_agent_id = GCL_response.items[MY_INDEX].id
    updated_data[index].enable_fail_back = True
    updated_data[index].enable_fail_over_on_collector_device = False

    try:
        PCBID_response = lm_api.patch_collector_by_id(
            id=GCL_response.items[index].id,
            body=updated_data[index])
    except ApiException as e:
        err_and_die(f"Exception when calling LMApi->patch_collector_by_id: {e}")

    try:
        GCBID_response = lm_api.get_collector_by_id(
            id=GCL_response.items[index].id,
            fields="id,backupAgentId,enableFailBack,enableFailOverOnCollectorDevice")
    except ApiException as e:
        print(f"Exception when calling LMApi->get_collector_by_id: {e}\n")

    if GCBID_response.backup_agent_id != GCL_response.items[MY_INDEX].id or \
      GCBID_response.enable_fail_back is not True or \
      GCBID_response.enable_fail_over_on_collector_device is not False:
        err_and_die(f"Failed, received values: "
              f"backup_agent_id={GCBID_response.backup_agent_id} "
              f"enable_fail_back={GCBID_response.enable_fail_back} "
              f"enable_fail_over_on_collector_device="
              f"{GCBID_response.enable_fail_over_on_collector_device}")
    else:
        logger.info('  Success')

logger.info('Exiting at bottom of script')
os._exit(0)
