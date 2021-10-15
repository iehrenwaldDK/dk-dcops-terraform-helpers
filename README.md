# dk-dcops-terraform-helpers

`lm-download-collector.py`
Downloads and installs a LogicMonitor collector if the correct paramaters are
supplied.  Those paramaters are:
  --api-id             required - single quoted string - API ID of LM user
  --api-key            required - single quoted string - API key of LM user
  --portal             required - string - Name of portal
  --collector-id       required - int - ID number of the collector to download
  --collector-size     optional - string - small/medium/large
  --collector-version  optional - int - Collector version to download
  --collector-ea       optional - bool - Use early access/beta collector

