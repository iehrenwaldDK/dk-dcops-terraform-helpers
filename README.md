# dk-dcops-terraform-helpers

Downloads and installs a LogicMonitor collector if the correct paramaters are  
supplied.  Those paramaters are:  
  --acess-id           required - single quoted string - API ID of LM user  
  --access-key         required - single quoted string - API key of LM user  
  --collector-id       required - int - ID number of the collector to download  
  --company            required - string - Name of portal  
  --collector-size     optional - string - small/medium/large  
  --collector-version  optional - int - Collector version to download  
  --collector-ea       optional - bool - Use early access/beta collector  

