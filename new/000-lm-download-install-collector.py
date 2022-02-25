#!/usr/bin/env python3

import argparse
import logging
import os
import subprocess
import tempfile
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
parser.add_argument('--collector-id', type=int, help='LM Collector ID to operator on', required=True)
parser.add_argument('--collector-os-arch', type=str, help='OS and Arch string recognized by LM API, most likely Linux64 or Windows64', required=False, default='Linux64', choices=['Linux32', 'Linux64', 'Windows32', 'Windows64'])
parser.add_argument('--collector-size', type=str, help='Collector size', required=False, default='medium', choices=['nano', 'small', 'medium', 'large'])
parser.add_argument('--collector-ea', action='store_true', help='Download latest Early Access collector', required=False, default=False)
parser.add_argument('--skip-download', action='store_true', help='Do not download installer, but still run installer', required=False, default=False)
parser.add_argument('--skip-install', action='store_true', help='Do not run LM Collector installer', required=False, default=False)
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

# Validate that the passed collector ID exists
logger.info('Searching for a collector with id %s', args.collector_id)
try:
    GCBID_response = lm_api.get_collector_by_id(id=args.collector_id)
except ApiException as e:
    err_and_die(f'Exception when calling LMApi->get_collector_by_id: {e}')

if not GCBID_response.id:
    err_and_die(f'  Search for collector id {args.collector_id} did not find any results')
else:
    logger.info(f'  Found %s', GCBID_response.hostname)

# Download the collector installer
if args.skip_download:
    logger.info('Skip download requested')
else:
    logger.info('Downloading the installer binary for collector id %s', args.collector_id)
    try:
        GCI_response = lm_api.get_collector_installer(
            collector_id=args.collector_id,
            os_and_arch=args.collector_os_arch,
            collector_size=args.collector_size,
            use_ea=args.collector_ea)
        if GCI_response.status != 200:
            err_and_die(f'HTTP response code from download request was {GCI_response.status}')
        logger.debug('LM API replied with code %s to GCI_response', GCI_response.status)
    except ApiException as e:
        err_and_die(f'Exception when calling LMApi->getCollectorInstaller: {e}')

    installer_bin = tempfile.NamedTemporaryFile(delete=False)
    installer_bin.write(GCI_response.data)
    installer_bin.close()

# Run the installer
if args.skip_install:
    logger.info('Skip installer execution requested')
else:
    logger.debug('Making installer %s executable', installer_bin.name)
    os.chmod(installer_bin.name, 0o755)
    logger.info('Running LM Collector installer')
    runner = subprocess.run([installer_bin.name, '-m', '-y'])
    if runner.returncode != 0:
        err_and_die('LM Collector installer did not exit cleanly')

logger.info('Exiting at bottom of script')
os._exit(0)

