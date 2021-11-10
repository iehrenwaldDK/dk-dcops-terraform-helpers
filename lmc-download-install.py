#!/usr/bin/python3

from __future__ import print_function
import getopt
import os
import subprocess
import sys
import tempfile
from pprint import pprint
import logicmonitor_sdk
from logicmonitor_sdk.rest import ApiException

print("LogicMonitor Collector download script starting")

if os.geteuid() != 0:
    sys.exit("You need to be root to run this.\n")

COMPANY_SET = False
COLLECTOR_ID = ''
COLLECTOR_VERSION = ''
COLLECTOR_SIZE = 'medium'
COLLECTOR_EA = 'false'
COLLECTOR_OSANDARCH = 'Linux64'
COLLECTOR_GROUP_AB = 'true'
ESCALATION_CHAIN = ''
SKIP_DOWNLOAD = False
SKIP_INSTALL = False
configuration = logicmonitor_sdk.Configuration()

try:
    options, arguments = getopt.getopt(sys.argv[1:], "",
                       ['access-id=', 'access-key=', 'company=', 'collector-id=',
                    'collector-size=', 'collector-version=', 'collector-ea=',
                    'escalation-chain=', 'collector-group-ab=',
                    'skip-download=', 'skip-install='])
except getopt.GetoptError as e:
    print(f"{e}")
    sys.exit(2)
for opt, arg in options:
    if opt in ('--company'):
        print(f"Found company arg: {arg}")
        configuration.company = arg
        COMPANY_SET = True
    if opt in ('--access-id'):
        print(f"Found access-id arg: {arg}")
        configuration.access_id = arg
    if opt in ('--access-key'):
        print(f"Found access-key arg: {arg}")
        configuration.access_key = arg
    if opt in ('--collector-id'):
        print(f"Found collector-id arg: {arg}")
        COLLECTOR_ID = arg
    if opt in ('--collector-version'):
        print(f"Found collector-version arg: {arg}")
        COLLECTOR_VERSION = arg
    if opt in ('--collector-size'):
        print(f"Found collector-size arg: {arg}")
        COLLECTOR_SIZE = arg
    if opt in ('--collector-ea'):
        print(f"Found collector-ea arg: {arg}")
        COLLECTOR_EA = arg
    if opt in ('--escalation-chain'):
        print(f"Found esclation-chain arg: {arg}")
        ESCALATION_CHAIN = arg
    if opt in ('--collector-group-ab'):
        print(f"Found collector-group-ab: {arg}")
        COLLECTOR_GROUP_AB = arg
    if opt in ('--skip-download'):
        print(f"Found skip-download: {arg}")
        SKIP_DOWNLOAD = arg
    if opt in ('--skip-install'):
        print(f"Found skip-install: {arg}")
        SKIP_INSTALL = arg

if not configuration.access_id or \
   not configuration.access_key or \
   not COMPANY_SET or \
   not COLLECTOR_ID:
    print("Not all required info is present, exiting")
    sys.exit(1)

api_instance = logicmonitor_sdk.LMApi(
    logicmonitor_sdk.ApiClient(configuration))

# Create and download the installer binary for the collector
print(f"Attempting to download installer for id={COLLECTOR_ID} size={COLLECTOR_SIZE} osAndArch={COLLECTOR_OSANDARCH}")
try:
    GCI_response = api_instance.get_collector_installer(
        COLLECTOR_ID,
        COLLECTOR_OSANDARCH,
        collector_size=COLLECTOR_SIZE,
        use_ea=COLLECTOR_EA)
    if GCI_response.status != 200:
        print(f"FATAL: HTTP Response status code was {GCI_response.status} and we want 200, exiting")
        sys.exit(1)
    print(f"LM API responded with code {GCI_response.status}")
    if SKIP_DOWNLOAD is False:
        print("Creating temporary file to hold installer")
        installer_bin = tempfile.NamedTemporaryFile(delete=False)
        print(f"Downloading collector installer to {installer_bin.name}")
        print("    Writing file")
        installer_bin.write(GCI_response.data)
        print("    Closing file")
        installer_bin.close()
    else:
        print("    skip-download was enabled")
except ApiException as E:
    print(f"FATAL: Exception when calling LMApi->getCollectorInstaller: {e}")

# Run the installer that was just downloaded
if SKIP_INSTALL is False:
    print("Making installer executable")
    os.chmod(installer_bin.name, 0o755)

    print(f"Running installer at {installer_bin.name}")
    runner = subprocess.run([installer_bin.name, "-m", "-y"])
    if runner.returncode != 0:
        print("LM Collector installer did not exit cleanly, aborting script")
        sys.exit(1)
else:
    print("    skip-install was enabled")

# If there was an escalation chain ID passed to the script, set the collector
#  to use it
if ESCALATION_CHAIN:
    print("Finding requested collector-down escalation chain")
    escalation_chain_filter = 'name:"' + ESCALATION_CHAIN + '"'

    try:
        GECL_response = api_instance.get_escalation_chain_list(
            filter=escalation_chain_filter)
    except ApiException as e:
        print(f"Exception when calling LMApi->getEscalationChainList: {e}\n")

    if GECL_response.items:
        escalation_chain_id = GECL_response.items[0].id
        print(f"    Found chain id {escalation_chain_id}")
    else:
        print("    Specified escalation chain not found, aborting")
        sys.exit(1)

    print("Retrieving new collector information")
    try:
        GCBID_response = api_instance.get_collector_by_id(COLLECTOR_ID)
    except ApiException as e:
        print(f"Exception when calling LMApi->getCollectorById: {e}\n")

    updated_data = GCBID_response
    updated_data.escalating_chain_id = escalation_chain_id

    print("Setting escalation chain ID on new collector")
    try:
        PCBI_response = api_instance.patch_collector_by_id(
            COLLECTOR_ID, updated_data)
    except ApiException as e:
        print(f"Exception when calling LMApi->updateCollectorById: {e}\n")

# If collector group auto-balancing was enabled through the script arguments,
#  enable it
if COLLECTOR_GROUP_AB:
    print(f"Finding collector group id {GCBID_response.collector_group_id} for autobalancing")
    try:
        GCGI_response = api_instance.get_collector_group_by_id(GCBID_response.collector_group_id)
    except ApiException as e:
        print(f"Exception when calling LMApi->get_collector_group_by_id: {e}\n")

    updated_data = GCGI_response
    updated_data.auto_balance = 'true'
    updated_data.auto_balance_instance_count_threshold = '10000'

    print("    Enabling auto-balancing on collector group")
    try:
        PCGBI_response = api_instance.patch_collector_group_by_id(
          GCBID_response.collector_group_id, updated_data)
    except ApiException as e:
        print(f"Exception when calling LMApi->patch_collector_group_by_id: {e}\n")

# Set the displayname of the collector device resource, instead of the
#  default of 127.0.0.1_collector_id
print("Setting correct hostname on collector device within LM")
try:
    GDBID_response = api_instance.get_device_by_id(GCBID_response.collector_device_id)
except ApiException as e:
    print(f"Exception when calling LMApi->getDeviceById: {e}\n")

updated_data = GDBID_response
updated_data.display_name = GCBID_response.hostname
try:
    PDBID_response = api_instance.patch_device(
        GCBID_response.collector_device_id,
        updated_data)
except ApiException as e:
    print(f"Exception when calling LMApi->patchDevice: {e}\n")

# If we've reached here, hopefully all has gone well
print("Exiting at bottom of the script")
