param(
    [Parameter(Mandatory=$False)][string] $log = "C:\lmc-download-install.log",
    [Parameter(Mandatory=$True)][string] $access_id,
    [Parameter(Mandatory=$True)][string] $access_key,
    [Parameter(Mandatory=$True)][string] $company,
    [Parameter(Mandatory=$True)][int] $collector_id,
    [Parameter(Mandatory=$True)][string] $escalation_chain,
    [Parameter(Mandatory=$False)][string] $collector_size = "medium",
    [Parameter(Mandatory=$False)][bool] $update_help = $False,
    [Parameter(Mandatory=$False)][bool] $install_nuget = $True,
    [Parameter(Mandatory=$False)][bool] $install_lmposh = $True
)

function WriteToLog($level, $message) {
    (Get-Date).ToString() + " - [" + $level + "] " + $message >> $log
}

WriteToLog("DEBUG", "Script started with:`n log=$log`n access_id=$access_id`n access_key=$access_key`n company=$company`n collector_id=$collector_id`n escalation_chain=$escalation_chain`n collector_size=$collector_size`n update_help=$update_help`n install_nuget=$install_nuget`n install_lmposh=$install_lmposh`n")

if($update_help -eq $True) {
    WriteToLog("INFO", "Updating help files")
    Update-Help -Force
}

if($install_nuget -eq $True) {
    WriteToLog("INFO", "Installing NuGet")
    Install-PackageProvider -Name NuGet -Force
}

if($install_lmposh -eq $True) {
    WriteToLog("INFO", "Installing LMPosh")
    Install-Module -Name LogicMonitor -Force
}

$access_key_ss  = ConvertTo-SecureString -String $access_key -AsPlainText -Force
$installer_path = Get-LogicMonitorCollectorInstaller -AccessId $access_id -AccessKey $access_key_ss -AccountName $company -Id $collector_id -Size $collector_size
WriteToLog("INFO", "Installer path is $installer_path")

if($installer_path -eq "Error"){
    WriteToLog("CRITICAL", "Error downloading collector, aborting")
    exit
}

# This silently installs the LM Collector using LocalSystem user.  If we
#  find that we need to monitor domain connecter resources, we'll need a 
#  LM specific domain user.  When if that happens, pass these args too:
#
WriteToLog("INFO", "Starting installer")
Invoke-Expression "$installer_path /q"

WriteToLog("INFO", "Getting escalation chain ID for $escalation_chain")
$escalation_chain_id = Get-LogicMonitorEscalationChain -AccessId $access_id -AccessKey $access_key_ss -AccountName $company -Name $escalation_chain
if($escalation_chain_id.Total -ne 1) {
    WriteToLog("ERROR", "Cannot find unique escalation chain with name $escalation_chain, skipping")
    exit
}

WriteToLog("INFO", "Setting escalation chain to $escalation_chain for $collector_id")
Update-LogicMonitorCollectorProperty -AccessId $access_id -AccessKey $access_key_ss -AccountName $company -Id $collector_id -PropertyNames @('escalatingChainId') -PropertyValues @($escalation_chain_id.Items.id)

WriteToLog("INFO", "Exiting at bottom of script")

