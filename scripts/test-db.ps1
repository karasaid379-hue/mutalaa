# scripts/test-db.ps1
# Creates the separate test database (mutalaa_test) next to the editorial one and applies the
# EF migrations to it with the idempotent SQL script. The pipeline's database tests
# (pytest -m veritabani) connect only to this database, never to the editorial one.
# Safe to run again: the script is idempotent and the database is only created when missing.
# Run from anywhere: powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/test-db.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

New-Item -ItemType Directory -Force .tmp | Out-Null
$sql = ".tmp/mutalaa-test-schema.sql"

dotnet ef migrations script --idempotent --project server/Mutalaa.Infrastructure --startup-project server/Mutalaa.Api --output $sql
if ($LASTEXITCODE -ne 0) {
    [Console]::Error.WriteLine("could not generate the migration script (exit code $LASTEXITCODE)")
    exit $LASTEXITCODE
}

# User and database names are read by the container's own sh, so .env changes need no edit here.
docker compose exec -T postgres sh -c 'createdb -U $POSTGRES_USER mutalaa_test 2>/dev/null; psql -U $POSTGRES_USER -l | grep -q mutalaa_test'
if ($LASTEXITCODE -ne 0) {
    [Console]::Error.WriteLine("could not create mutalaa_test (exit code $LASTEXITCODE)")
    exit $LASTEXITCODE
}

docker compose cp $sql postgres:/tmp/mutalaa-test-schema.sql
$code = $LASTEXITCODE
if ($code -eq 0) {
    docker compose exec -T postgres sh -c 'psql -U $POSTGRES_USER -d mutalaa_test -v ON_ERROR_STOP=1 -q -f /tmp/mutalaa-test-schema.sql'
    $code = $LASTEXITCODE
}
docker compose exec -T postgres rm -f /tmp/mutalaa-test-schema.sql

if ($code -ne 0) {
    [Console]::Error.WriteLine("applying the schema to mutalaa_test failed (exit code $code)")
    exit $code
}
Write-Output "mutalaa_test is ready"
