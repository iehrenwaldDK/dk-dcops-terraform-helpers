#!/usr/bin/python3

import os
import sys
import getopt
import requests
import json
import hashlib
import base64
import time
import hmac
import subprocess

def main(arg):
    portal = 'draftkings'
    api_id = ''
    api_key = ''
    collector_id = ''
    collector_version = ''
    collector_size = 'medium'
    collector_ea = 'false'

    # Are we root?
    if os.geteuid() != 0:
        sys.exit("You need to be root to run this.\n")

    try:
        options,arguments = getopt.getopt(sys.argv[1:], "", ['api-id=', 'api-key=', 'portal=', 'collector-id=', 'collector-size=', 'collector-version=', 'collector-ea='])

    except getopt.GetoptError as e:
        print("%s" % e)
        sys.exit(2)
    for opt,arg in options:
        if opt in ('--portal'):
            portal = arg
        if opt in ('--api-id'):
            api_id = arg
        if opt in ('--api-key'):
            api_key = arg
        if opt in ('--collector-id'):
            collector_id = arg
        if opt in ('--collector-version'):
            collector_version = arg
        if opt in ('--collector-size'):
            collector_size = arg
        if opt in ('--collector-ea'):
            collector_ea = arg
    if not api_id or not api_key or not portal or not collector_id:
        print("Not all required info is present, exiting")
        sys.exit(1)


    httpVerb = 'GET'

    #Adding the CollectorID to the URL
    resourcePath = '/setting/collectors/' + collector_id + '/installers/Linux64'
    queryParams  = '?collectorSize=' + collector_size

    # Version selection
    if collector_version and collector_ea == 'true':
        print("WARNING: LM_collector_version AND LM_collector_useEA specified, choosing versioned")
        queryParams += '&collectorVersion=' + collector_version
    if not collector_version and collector_ea == 'true':
        print("INFO: No collector version specified and useEA is true, choosing useEA")
        queryParams += '&useEA=true'
    elif collector_version:
        print("INFO: Collector version " + collector_version + " requested")
        queryParams += '&collectorVersion=' + collector_version
    else:
        print("INFO: No collector version requested, defaulting to GD")

    #Construct URL
    url = 'https://'+ portal +'.logicmonitor.com/santaba/rest' + resourcePath + queryParams

    #Get current time in milliseconds
    epoch = str(int(time.time() * 1000))

    # Empty
    data = ''

    #Concatenate Request details
    requestVars = httpVerb + epoch + data + resourcePath

    #Construct signature
    my_hmac = hmac.new(api_key.encode(), msg=requestVars.encode(),digestmod=hashlib.sha256).hexdigest()
    signature = base64.b64encode(my_hmac.encode())

    #Construct headers
    auth = 'LMv1 ' + api_id + ':' + signature.decode() + ':' + epoch
    headers = {'Content-Type':'application/json','Authorization':auth}

    #Make request
    print("Sending Collector Download request to LogicMonitor")
    response = requests.get(url, data=data, headers=headers)
    print("    Request response status code: ", response.status_code)

    if response.status_code != requests.codes.ok:
        print("Status code is not OK, cannot continue")
        sys.exit(1)

    print("Downloading Collector Installer")
    file_ = open('LogicMonitorSetup.bin', 'wb')
    file_.write(response.content)
    file_.close()

    #Give execute perm to collector install and install with the silent option
    print("Adding execute permissions to the collector download")
    subprocess.call(['chmod', '+x', 'LogicMonitorSetup.bin'])

    print("Starting collector install")
    subprocess.run(['./LogicMonitorSetup.bin', '-y', '-m'])
    print("Exiting at bottom of script.")


if __name__ == "__main__":
    main(sys.argv[1:])
