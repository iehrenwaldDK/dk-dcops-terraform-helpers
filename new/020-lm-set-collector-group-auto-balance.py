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
parser.add_argument('--cg-id', type=int, help='LM Collector Group ID', required=False)
parser.add_argument('--cg-name', type=str, help='Collector Group name, instead of id', required=False)
parser.add_argument('--action', type=str, help='Operation to perform', required=True, choices=['enable', 'disable'])
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

if not args.cg_id and not args.cg_name:
    err_and_die('Need to specify either --cg-id or --cg-name')
if args.cg_id and args.cg_name:
    err_and_die('Only need one of --cg-id or --cg-name')

if args.cg_name:
    logger.info('Searching for a collector group named %s', args.cg_name)
    try:
        GCGL_filter   = 'name:"' + args.cg_name + '"'
        GCGL_response = lm_api.get_collector_group_list(filter=GCGL_filter)
    except ApiException as e:
        err_and_die('Exception when calling LMApi->get_collector_group_list: {e}')

    if GCGL_response.total == 0:
        err_and_die('  Did not find a collector group with that name')
    if GCGL_response.total == 1:
        name_to_cgid = GCGL_response.items[0].id
        logger.info('  Found collector group id %s', name_to_cgid)
    else:
        err_and_die('  More than one search result was returned, cannot read minds')

if args.cg_id or name_to_cgid:
    resolved_cgid = name_to_cgid if name_to_cgid else args_cg_id

    logger.info('Searching for collector group id %s', resolved_cgid)
    try:
        GCGBID_response = lm_api.get_collector_group_by_id(id=resolved_cgid)
    except ApiException as e:
        err_and_die(f"Exception when calling LMApi->get_collector_by_id: {e}")

    if GCGBID_response.id:
        resolved_cgid = GCGBID_response.id
        logger.info('  Found collector group %s', GCGBID_response.name)
    else:
        err_and_die('  Did not find a collector group with that id')

# Enable or disable auto-balancing on collector group
logger.info('Setting auto-balance to %s on collector group id %s', args.action, resolved_cgid)
try:
    ab_state = 'true' if args.action == 'enable' else 'false'

    updated_data = GCGBID_response
    updated_data.auto_balance = ab_state
    updated_data.auto_balance_instance_count_threshold = '10000'

    PCGBID_response = lm_api.patch_collector_group_by_id(
        id=resolved_cgid,
        body=updated_data)
except ApiException as e:
    err_and_die(f'Exception when calling LMApi->patch_collector_group_by_id: {e}')

logger.info('Exiting at bottom of script')
os._exit(0)
