#!/usr/bin/env python3

from __future__ import print_function
import getopt
import os
import subprocess
import sys
import tempfile
from pprint import pprint
from random import randint
from time import sleep
import logicmonitor_sdk
from logicmonitor_sdk.rest import ApiException

print("LogicMonitor Collector download/install/configure script starting")

if os.geteuid() != 0:
    sys.exit("You need to be root to run this.\n")

COMPANY_SET = False
COLLECTOR_ID = ''
COLLECTOR_VERSION = ''
COLLECTOR_SIZE = 'medium'
COLLECTOR_EA = 'false'
COLLECTOR_OSANDARCH = 'Linux64'
COLLECTOR_GROUP_ID = ''
COLLECTOR_GROUP_AB = 'false'
ENABLE_FAILOVER = 'false'
ESCALATION_CHAIN = ''
SKIP_DOWNLOAD = False
SKIP_INSTALL = False
SNMP_SECURITY = ''
SNMP_AUTH = ''
SNMP_AUTH_TOKEN = ''
SNMP_PRIV = ''
SNMP_PRIV_TOKEN = ''

configuration = logicmonitor_sdk.Configuration()

try:
    options, arguments = getopt.getopt(sys.argv[1:], "",
                       ['access-id=', 'access-key=', 'company=', 'collector-id=',
                    'collector-size=', 'collector-version=', 'collector-ea=',
                    'escalation-chain=', 'collector-group-ab=',
                    'collector-group-id=', 'enable-failover='
                    'skip-download', 'skip-install',
                    'snmp-security=', 'snmp-auth-token=', 'snmp-auth=',
                    'snmp-priv-token=', 'snmp-priv='])
except getopt.GetoptError as e:
    print(f"{e}")
    sys.exit(2)
for opt, arg in options:
    if opt in ('--company'):
        configuration.company = arg
        COMPANY_SET = True
    elif opt in ('--access-id'):
        configuration.access_id = arg
    elif opt in ('--access-key'):
        configuration.access_key = arg

    elif opt in ('--collector-id'):
        COLLECTOR_ID = arg
    elif opt in ('--collector-version'):
        COLLECTOR_VERSION = arg
    elif opt in ('--collector-size'):
        COLLECTOR_SIZE = arg
    elif opt in ('--collector-ea'):
        COLLECTOR_EA = arg

    elif opt in ('--escalation-chain'):
        ESCALATION_CHAIN = arg
    elif opt in ('--collector-group-ab'):
        COLLECTOR_GROUP_AB = arg
    elif opt in ('--collector-group-id'):
        COLLECTOR_GROUP_ID = arg

    elif opt in ('--skip-download'):
        SKIP_DOWNLOAD = True
    elif opt in ('--skip-install'):
        SKIP_INSTALL = True

    elif opt in ('--snmp-security'):
        SNMP_SECURITY = arg
    elif opt in ('--snmp-auth'):
        SNMP_AUTH = arg
    elif opt in ('--snmp-priv'):
        SNMP_PRIV = arg
    elif opt in ('--snmp-auth-token'):
        SNMP_AUTH_TOKEN = arg
    elif opt in ('--snmp-priv-token'):
        SNMP_PRIV_TOKEN = arg

    elif opt in ('--enable-failover'):
        ENABLE_FAILOVER = True

if not configuration.access_id or \
   not configuration.access_key or \
   not COMPANY_SET or \
   not COLLECTOR_ID:
    print("Not all required info is present, exiting")
    sys.exit(1)

api_instance = logicmonitor_sdk.LMApi(
    logicmonitor_sdk.ApiClient(configuration))

# Create and download the installer binary for the collector
try:
    GCI_response = api_instance.get_collector_installer(
        collector_id=COLLECTOR_ID,
        os_and_arch=COLLECTOR_OSANDARCH,
        collector_size=COLLECTOR_SIZE,
        use_ea=COLLECTOR_EA)
    if GCI_response.status != 200:
        print(f"FATAL: HTTP Response code was {GCI_response.status} and we want 200, exiting")
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
        GCBID_response = api_instance.get_collector_by_id(id=COLLECTOR_ID)
    except ApiException as e:
        print(f"Exception when calling LMApi->getCollectorById: {e}\n")

    updated_data = GCBID_response
    updated_data.escalating_chain_id = escalation_chain_id

    print("Setting escalation chain ID on new collector")
    try:
        PCBID_response = api_instance.patch_collector_by_id(
            id=COLLECTOR_ID,
            body=updated_data)
    except ApiException as e:
        print(f"Exception when calling LMApi->updateCollectorById: {e}\n")

# If collector group auto-balancing was enabled through the script arguments,
#  enable it
if COLLECTOR_GROUP_AB:
    print(f"Finding collector group id {GCBID_response.collector_group_id} for autobalancing")
    try:
        GCGBID_response = api_instance.get_collector_group_by_id(GCBID_response.collector_group_id)
    except ApiException as e:
        print(f"Exception when calling LMApi->get_collector_group_by_id: {e}\n")

    updated_data = GCGBID_response
    updated_data.auto_balance = 'true'
    updated_data.auto_balance_instance_count_threshold = '10000'

    print("    Enabling auto-balancing on collector group")
    try:
        PCGBID_response = api_instance.patch_collector_group_by_id(
          id=GCBID_response.collector_group_id,
          body=updated_data)
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
    PD_response = api_instance.patch_device(
        id=GCBID_response.collector_device_id,
        body=updated_data)
except ApiException as e:
    print(f"Exception when calling LMApi->patchDevice: {e}\n")

# Set the custom properties of the collector device resource to include SNMPv3
#  settings
if SNMP_SECURITY and SNMP_AUTH and SNMP_AUTH_TOKEN and SNMP_PRIV and SNMP_PRIV_TOKEN:
    print(f"Setting SNMPv3 custom properties on device {GCBID_response.collector_device_id}")
    updated_data.custom_properties.append({'name':'snmp.security', 'value': SNMP_SECURITY})
    updated_data.custom_properties.append({'name':'snmp.auth', 'value': SNMP_AUTH})
    updated_data.custom_properties.append({'name':'snmp.priv', 'value': SNMP_PRIV})
    updated_data.custom_properties.append({'name':'snmp.authToken', 'value': SNMP_AUTH_TOKEN})
    updated_data.custom_properties.append({'name':'snmp.privToken', 'value': SNMP_PRIV_TOKEN})

    try:
        PD_response = api_instance.patch_device(
                        id=GCBID_response.collector_device_id,
                        body=updated_data,
                        op_type='replace')
    except ApiException as e:
        print(f"Exception when calling LMApi->patchDevice: {e}\n")

if ENABLE_FAILOVER:
    if not COLLECTOR_GROUP_ID:
        print("Collector failover setup requested but no collector group id provided, aborting")
        sys.exit(1)

    # Why are we sleeping a random time?  So we give all collectors a chance
    #  to download/install/configure/verify.  It's safe for this to run on
    #  all collectors.
    SLEEP_MIN=120
    SLEEP_MAX=300
    sleep_time = randint(SLEEP_MIN,SLEEP_MAX)
    print(f"Sleeping {sleep_time} seconds and then beginning failover setup")
    sleep(sleep_time)

    print(f">> Finding collectors in collector group '{COLLECTOR_GROUP_ID}'")
    try:
        GCL_filter = 'collectorGroupId:"' + str(COLLECTOR_GROUP_ID) + '"'
        GCL_response = api_instance.get_collector_list(
            fields="id,backupAgentId,enableFailBack,enableFailOverOnCollectorDevice",
            filter=GCL_filter)
    except ApiException as e:
        print(f"Exception when calling LMApi->getEscalationChainList: {e}\n")

    if GCL_response.total == 0:
        print(">>> No matches for the search, aborting")
        sys.exit(1)

    if GCL_response.total < 2:
        print(">>> There are less than two collectors in the group, aborting")
        sys.exit(1)

    MY_INDEX = 0
    updated_data = GCL_response.items
    # This is a little tricky
    for index,element in enumerate(updated_data):
        if index+1 >= GCL_response.total:
            MY_INDEX = 0
        else:
            MY_INDEX += 1

        print(f">> Setting collector {GCL_response.items[MY_INDEX].id} as "
              f"backup for {updated_data[index].id}")
        updated_data[index].backup_agent_id = GCL_response.items[MY_INDEX].id
        updated_data[index].enable_fail_back = True
        updated_data[index].enable_fail_over_on_collector_device = False

        try:
            PCBID_response = api_instance.patch_collector_by_id(
                id=GCL_response.items[index].id,
                body=updated_data[index])
        except ApiException as e:
            print(f"Exception when calling LMApi->patch_collector_by_id: {e}\n")

        print(">>> Verifying")
        try:
            GCBID_response = api_instance.get_collector_by_id(
                id=GCL_response.items[index].id,
                fields="id,backupAgentId,enableFailBack,enableFailOverOnCollectorDevice")
        except ApiException as e:
            print(f"Exception when calling LMApi->getCollectorById: {e}\n")

        if GCBID_response.backup_agent_id != GCL_response.items[MY_INDEX].id or \
          GCBID_response.enable_fail_back is not True or \
          GCBID_response.enable_fail_over_on_collector_device is not False:
            print(">>>> Failed, received values: "
                   f"backup_agent_id={GCBID_response.backup_agent_id} "
                   f"enable_fail_back={GCBID_response.enable_fail_back} "
                   f"enable_fail_over_on_collector_device="
                   f"{GCBID_response.enable_fail_over_on_collector_device}")
            sys.exit(1)
        else:
            print(">>>> Success")

# If we've reached here, hopefully all has gone well
print("Exiting at bottom of the script")
