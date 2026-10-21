# scripts/restore-db.ps1
# Restores a pg_dump file (positional argument) into the editorial database.
# pg_restore runs with --clean --if-exists: existing objects in the dump are dropped first.
# Use it only with a backup you just took or one you have checked.
# powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/restore-db.ps1 data/backups/mutalaa-YYYYMMDD-HHmmss.dump
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$File
)
$ErrorActionPreference = "Stop"

# Resolve the argument against the caller's directory before moving to the repository root.
if (-not (Test-Path -LiteralPath $File -PathType Leaf)) {
    [Console]::Error.WriteLine("Backup file not found: $File")
    exit 2
}
$full = (Resolve-Path -LiteralPath $File).Path
Set-Location (Join-Path $PSScriptRoot "..")
# A relative path avoids "C:\..." being read as a service name by docker compose cp.
$source = Resolve-Path -LiteralPath $full -Relative

docker compose cp $source postgres:/tmp/restore.dump
if ($LASTEXITCODE -ne 0) { [Console]::Error.WriteLine("docker compose cp failed"); exit $LASTEXITCODE }

docker compose exec -T postgres sh -c 'pg_restore -U $POSTGRES_USER -d $POSTGRES_DB --clean --if-exists --single-transaction /tmp/restore.dump'
$code = $LASTEXITCODE

docker compose exec -T postgres rm -f /tmp/restore.dump
if ($code -ne 0) { [Console]::Error.WriteLine("pg_restore failed"); exit $code }
