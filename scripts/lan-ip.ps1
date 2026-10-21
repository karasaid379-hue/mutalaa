# scripts/lan-ip.ps1
# Prints the computer's IPv4 address on the given network adapter (default: Wi-Fi).
# The phone reaches Metro (8081) and the S3 store (8333) through this address.
# powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/lan-ip.ps1 [-InterfaceAlias "Ethernet"]
param(
    [string]$InterfaceAlias = "Wi-Fi"
)
$ErrorActionPreference = "Stop"

$addresses = @(Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias $InterfaceAlias -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -notlike "169.254.*" } |
    Select-Object -ExpandProperty IPAddress)

if ($addresses.Count -eq 0) {
    $known = (Get-NetIPAddress -AddressFamily IPv4 | Select-Object -ExpandProperty InterfaceAlias | Sort-Object -Unique) -join ", "
    [Console]::Error.WriteLine("No IPv4 address on adapter '$InterfaceAlias'. Adapters with IPv4: $known")
    exit 1
}

$addresses
