param(
    [Parameter(Mandatory=$True)][string] $access_id,
    [Parameter(Mandatory=$True)][string] $access_key,
    [Parameter(Mandatory=$True)][string] $company,
    [Parameter(Mandatory=$True)][string] $collector_id,
    [Parameter(Mandatory=$True)][string] $escalation_chain,
    [Parameter(Mandatory=$False)][string] $collector_size = "medium",
    [Parameter(Mandatory=$False)][bool] $update_help = $False,
    [Parameter(Mandatory=$False)][bool] $install_nuget = $True,
    [Parameter(Mandatory=$False)][bool] $install_lmposh = $True
)

if($update_help -eq $True) {
    Write-Host "Updating help files"
    Update-Help -Force
}

if($install_nuget -eq $True) {
    Write-Host "Installing NuGet"
    Install-PackageProvider -Name NuGet -Force
}

if($install_lmposh -eq $True) {
    Write-Host "Installing LMPosh"
    Import-Module -Name LogicMonitor -Force
}

$access_key_ss  = ConvertTo-SecureString -String $access_key -AsPlainText -Force
$installer_path = Get-LogicMonitorCollectorInstaller -AccessId $access_id -AccessKey $access_key_ss -AccountName $company -Id $collector_id -Size $collector_size

if($installer_path -eq "Error"){
    Write-Host -ForegroundColor Red "Error downloading collector, aborting"
    exit
}

# This silently installs the LM Collector using LocalSystem user.  If we
#  find that we need to monitor domain connecter resources, we'll need a 
#  LM specific domain user.  When if that happens, pass these args too:
#
Write-Host "Installer path is $installer_path"
Invoke-Expression "$installer_path /q"

Write-Host "Getting escalation chain ID for $escalation_chain"
$escalation_chain_id = Get-LogicMonitorEscalationChain -AccessId $access_id -AccessKey $access_key_ss -AccountName $company -Name $escalation_chain
if($escalation_chain_id.Total -ne 1) {
    Write-Host "Cannot find unique escalation chain with name $escalation_chain , aborting"
    exit
}

Write-Host "Setting escalation chain to $escalation_chain for $collector_id"
Update-LogicMonitorCollectorProperty -AccessId $access_id -AccessKey $access_key_ss -AccountName $company -Id $collector_id -PropertyNames @('escalatingChainId') -PropertyValues @($escalation_chain_id.Items.id)

Write-Host "Exiting at bottom of script"

