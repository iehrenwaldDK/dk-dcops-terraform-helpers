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
parser.add_argument('--escalation-chain', type=str, help='Name of Escalation Chain to use if collector is unreachable', required=True)
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

# Search for escalation chain
logger.info('Searching for an escalation chain named %s', args.escalation_chain)
try:
    GECL_filter = 'name:"' + args.escalation_chain + '"'
    GECL_response = lm_api.get_escalation_chain_list(filter=GECL_filter)
except ApiException as e:
    err_and_die(f"Exception when calling LMApi->getEscalationChainList: {e}")

if GECL_response.total == 1:
    logger.info('  Found escalation chain id %s', GECL_response.items[0].id)
else:
    err_and_die('  Did not find an escalation chain with that name')

# Search for collector
logger.info('Searching for a collector with id %s', args.collector_id)
try:
    GCBID_fields = 'id,hostname,collectorDeviceId'
    GCBID_response = lm_api.get_collector_by_id(id=args.collector_id, fields=GCBID_fields)
except ApiException as e:
    err_and_die(f'Exception when calling LMApi->get_collector_by_id: {e}')

if GCBID_response.id:
    logger.info(f'  Found %s', GCBID_response.hostname)
else:
    err_and_die(f'  Search for collector id {args.collector_id} did not find any results')

# Set escalation chain on collector
logger.info('Set escalation chain %s on collector %s', GECL_response.items[0].id, GCBID_response.id)
updated_data = GCBID_response
updated_data.escalating_chain_id = GECL_response.items[0].id

try:
    PCBID_response = lm_api.patch_collector_by_id(
        id=GCBID_response.id,
        body=updated_data)
except ApiException as e:
    err_and_die(f'Exception when calling LMApi->updateCollectorById: {e}')

logger.info('Exiting at bottom of script')
os._exit(0)
