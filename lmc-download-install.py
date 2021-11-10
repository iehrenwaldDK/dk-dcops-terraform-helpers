#!/usr/bin/python3

from __future__ import print_function
import base64
import getopt
import hashlib
import hmac
import json
import logicmonitor_sdk
from logicmonitor_sdk.rest import ApiException
import os
import requests
import subprocess
import sys
import tempfile
import time
from pprint import pprint

print("LogicMonitor Collector download script starting")

if os.geteuid() != 0:
    sys.exit("You need to be root to run this.\n")

company_set = False
collector_id = ''
collector_version = ''
collector_size = 'medium'
collector_ea = 'false'
collector_osAndArch = 'Linux64'
collector_group_name = ''
escalation_chain = ''
configuration = logicmonitor_sdk.Configuration()

try:
    options, arguments = getopt.getopt(sys.argv[1:], "",
                                       ['access-id=', 'access-key=', 'company=', 'collector-id=',
                                        'collector-size=', 'collector-version=', 'collector-ea=',
                                        'escalation-chain=', 'collector-group-name='])
except getopt.GetoptError as e:
    print("%s" % e)
    sys.exit(2)
for opt, arg in options:
    if opt in ('--company'):
        print("Found company arg: %s" % arg)
        configuration.company = arg
        company_set = True
    if opt in ('--access-id'):
        print("Found access-id arg: %s" % arg)
        configuration.access_id = arg
    if opt in ('--access-key'):
        print("Found access-key arg: %s" % arg)
        configuration.access_key = arg
    if opt in ('--collector-id'):
        print("Found collector-id arg: %s" % arg)
        collector_id = arg
    if opt in ('--collector-version'):
        print("Found collector-version arg: %s" % arg)
        collector_version = arg
    if opt in ('--collector-size'):
        print("Found collector-size arg: %s" % arg)
        collector_size = arg
    if opt in ('--collector-ea'):
        print("Found collector-ea arg: %s" % arg)
        collector_ea = arg
    if opt in ('--escalation-chain'):
        print("Found esclation-chain arg: %s" % arg)
        escalation_chain = arg
    if opt in ('--collector-group-name'):
        print("Found collector-group-name: %s" % arg)
        collector_group_name = arg

if not configuration.access_id or \
   not configuration.access_key or \
   not company_set or \
   not collector_id:
    print("Not all required info is present, exiting")
    sys.exit(1)

api_instance = logicmonitor_sdk.LMApi(
    logicmonitor_sdk.ApiClient(configuration))

print("Attempting to download installer for id=%s size=%s osAndArch=%s" %
      (collector_id, collector_size, collector_osAndArch))
try:
    GCI_response = api_instance.get_collector_installer(
        collector_id,
        collector_osAndArch,
        collector_size=collector_size,
        use_ea=collector_ea)
    if GCI_response.status != 200:
        print("FATAL: HTTP Response status code was %d and we want 200, exiting")
        sys.exit(1)
    print("LM API responded with code %d" % GCI_response.status)
    print("Creating temporary file to hold installer")
    installer_bin = tempfile.NamedTemporaryFile(delete=False)
    print("Downloading collector installer to %s" % installer_bin.name)
    print("    Writing file")
    installer_bin.write(GCI_response.data)
    print("    Closing file")
    installer_bin.close()
except ApiException as E:
    print("FATAL: Exception when calling LMApi->getCollectorInstaller: %s" % e)

print("Making installer executable")
os.chmod(installer_bin.name, 0o755)

print("Running installer at %s" % installer_bin.name)
runner = subprocess.run([installer_bin.name, "-m", "-y"])
#print("Would have run installer\n")
if runner.returncode != 0:
    print("LM Collector installer did not exit cleanly, aborting script")
    sys.exit(1)

if escalation_chain:
    print("Finding requested collector-down escalation chain")
    escalation_chain_filter = 'name:"' + escalation_chain + '"'

    try:
        GECL_response = api_instance.get_escalation_chain_list(
            filter=escalation_chain_filter)
    except ApiException as e:
        print("Exception when calling LMApi->getEscalationChainList: %s\n" % e)

    if GECL_response.items:
        escalation_chain_id = GECL_response.items[0].id
        print("    Found chain id %d" % escalation_chain_id)
    else:
        print("    Specified escalation chain not found, aborting")
        sys.exit(1)

    print("Retrieving new collector information")
    try:
        GCBID_response = api_instance.get_collector_by_id(collector_id)
    except ApiException as e:
        print("Exception when calling LMApi->getCollectorById: %s\n" % e)

    updated_data = GCBID_response
    updated_data.escalating_chain_id = escalation_chain_id

    print("Setting escalation chain ID on new collector")
    try:
        PCBI_response = api_instance.patch_collector_by_id(
            collector_id, updated_data)
    except ApiException as e:
        print("Exception when calling LMApi->updateCollectorById: %s\n" % e)

if collector_group_name:
    print("Finding requested collector group to enable auto-balancing")
    collector_group_filter = 'name:"' + collector_group_name + '"'

    try:
        GCGL_response = api_instance.get_collector_group_list(
            filter=collector_group_filter)
    except ApiException as e:
        print("Exception when calling LMApi->get_collector_group_list: %s\n" % e)

    if GCGL_response.total == 1:
        collector_group_id = GCGL_response.items[0].id
        print("    Found collector group id %d" % collector_group_id)
    else:
        print("    Search did not return exactly one result, aborting")
        sys.exit(1)

    print("Retrieving collector group information")
    try:
        GCGI_response = api_instance.get_collector_group_by_id(collector_group_id)
    except ApiException as e:
        print("Exception when calling LMApi->get_collector_group_by_id : %s\n" % e)

    updated_data = GCGI_response
    updated_data.auto_balance = 'true'
    updated_data.auto_balance_instance_count_threshold = '10000'

    print("Enabling auto-balancing on collector group")
    try:
        PCGBI_response = api_instance.patch_collector_group_by_id(
          collector_group_id, updated_data)
    except ApiException as e:
        print("Exception when calling LMApi->patch_collector_group_by_id : %s\n" % e)

print("Exiting at bottom of the script")
