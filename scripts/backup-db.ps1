# scripts/backup-db.ps1
# Takes a custom-format pg_dump of the editorial database into data/backups/.
# The dump is checked with pg_restore --list and only then renamed to its final name,
# so an interrupted run never leaves a file that looks like a good backup.
# Also archives data/gold when it exists (hand-made gold sets cannot be regenerated).
# Run from anywhere: powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/backup-db.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
New-Item -ItemType Directory -Force data/backups | Out-Null
$final = "data/backups/mutalaa-$stamp.dump"
$partial = "$final.partial"

# The user and database names are read by the container's own sh, so .env changes need no edit here.
docker compose exec -T postgres sh -c 'pg_dump -U $POSTGRES_USER -d $POSTGRES_DB -Fc -f /tmp/mutalaa.dump'
$code = $LASTEXITCODE
if ($code -eq 0) {
    docker compose exec -T postgres sh -c 'pg_restore --list /tmp/mutalaa.dump > /dev/null'
    $code = $LASTEXITCODE
}
if ($code -eq 0) {
    docker compose cp postgres:/tmp/mutalaa.dump $partial
    $code = $LASTEXITCODE
}

# The full dump inside the container is removed on success and on failure.
docker compose exec -T postgres rm -f /tmp/mutalaa.dump

if ($code -ne 0) {
    Remove-Item -LiteralPath $partial -Force -ErrorAction SilentlyContinue
    [Console]::Error.WriteLine("backup failed (exit code $code); no backup file was kept")
    exit $code
}
Move-Item -LiteralPath $partial -Destination $final

if (Test-Path data/gold) {
    # Compress-Archive in Windows PowerShell 5.1 needs a .zip destination, so the temporary name ends in .zip.
    $goldTemp = "data/backups/gold-$stamp.partial.zip"
    Compress-Archive -Path data/gold -DestinationPath $goldTemp -Force
    Move-Item -LiteralPath $goldTemp -Destination "data/backups/gold-$stamp.zip"
}

Write-Output $final
