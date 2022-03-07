# dk-dcops-terraform-helpers
This script is used with cloud-init for the most part.  But if you want to manually play with it:



usage: lmc-util.py [-h] --portal PORTAL --access-id ACCESS_ID --access-key ACCESS_KEY [--log-file [LOG_FILE]] [--log-level [{DEBUG,INFO,WARNING,ERROR,CRITICAL}]]
                   {install,devgrp,devname,echain,snmp,cgab,cgfo,rad} ...

positional arguments:
  {install,devgrp,devname,echain,snmp,cgab,cgfo,rad}
                        Desired action to perform
    install             Download and install collector
    devgrp              Add collector VM to a device group
    devname             Set collector VM device name
    echain              Set collector escalation chain
    snmp                Set collector SNMP custom properties
    cgab                Set collector group auto balance
    cgfo                Set collector group failover
    rad                 Run device datasource auto-discovery

optional arguments:
  -h, --help            show this help message and exit
  --portal PORTAL       LM Portal Name (default: None)
  --access-id ACCESS_ID
                        LM API ID (default: None)
  --access-key ACCESS_KEY
                        LM API Key (default: None)
  --log-file [LOG_FILE]
                        Write to this log file (default: /tmp/lm-collector-install-setup.log)
  --log-level [{DEBUG,INFO,WARNING,ERROR,CRITICAL}]
                        Log level, default is INFO (default: INFO)

