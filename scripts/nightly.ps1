# scripts/nightly.ps1
# Local nightly run on the REAL Tanzil data (the CI workflow .github/workflows/nightly.yml only
# runs the fixture tests; data/ is not in git). Steps, in order, stopping at the first failure:
#   sources check -> ingest (both variants) -> normalize -> anchor -> qa run
#   -> [export pg --dry-run, export pg]
#   -> structure data (A11): ingest ust-veri -> anchor -> qa run -> [export pg --dry-run, export pg]
#   -> export test-vectors --tanzil-ornekleri --check
#   -> pytest -m degismezlik with MUTALAA_DEGISMEZLIK_ZORUNLU=1 (a missing file is a failure).
# Requires the files under data/gelen/tanzil/<YYYY-AA-GG>/ (stage A10.0) and
# data/gelen/tanzil-ust-veri/<YYYY-AA-GG>/ (stage A11.0). Nothing is downloaded.
# The structure chain also reads data/gelen/medine-604-duzen and data/gelen/quran-meta when
# present (QA verification inputs; the measurements are reported as skipped when absent).
# The exit code of the failing step is returned (0 ok, 1 QA gate or test failed, 2 input error).
#
# -ExportPg   also loads the units into PostgreSQL (the connection string comes from the
#             environment or pipeline/.env, never from an argument) and runs the PostgreSQL half
#             of the immutability test 3 and 4. Without it those two tests are left out.
#
# Run from anywhere: powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/nightly.ps1
param(
    [switch]$ExportPg
)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$env:PYTHONUTF8 = "1"

function Invoke-Step {
    param([string]$Name, [string[]]$UvArgs)
    Write-Output "== $Name"
    & uv --directory pipeline run @UvArgs
    if ($LASTEXITCODE -ne 0) {
        [Console]::Error.WriteLine("step failed: $Name (exit code $LASTEXITCODE)")
        exit $LASTEXITCODE
    }
}

if (-not (Test-Path "data/gelen/tanzil" -PathType Container)) {
    [Console]::Error.WriteLine("data/gelen/tanzil is missing: download the Tanzil files first (A10.0)")
    exit 2
}

if (-not (Test-Path "data/gelen/tanzil-ust-veri" -PathType Container)) {
    [Console]::Error.WriteLine("data/gelen/tanzil-ust-veri is missing: download quran-data.xml first (A11.0)")
    exit 2
}

Invoke-Step "sources check" @("mutalaa", "sources", "check")
Invoke-Step "ingest uthmani" @("mutalaa", "ingest", "tanzil", "--variant", "uthmani")
Invoke-Step "ingest simple-clean" @("mutalaa", "ingest", "tanzil", "--variant", "simple-clean")
Invoke-Step "normalize" @("mutalaa", "normalize", "--source", "tanzil-uthmani")
Invoke-Step "anchor" @("mutalaa", "anchor", "--source", "tanzil-uthmani")
Invoke-Step "qa run" @("mutalaa", "qa", "run", "--source", "tanzil-uthmani")
if ($ExportPg) {
    Invoke-Step "export pg (dry run)" @("mutalaa", "export", "pg", "--source", "tanzil-uthmani", "--dry-run")
    Invoke-Step "export pg" @("mutalaa", "export", "pg", "--source", "tanzil-uthmani")
}
Invoke-Step "ingest ust-veri" @("mutalaa", "ingest", "tanzil", "--variant", "ust-veri")
Invoke-Step "anchor ust-veri" @("mutalaa", "anchor", "--source", "tanzil-ust-veri")
Invoke-Step "qa run ust-veri" @("mutalaa", "qa", "run", "--source", "tanzil-ust-veri")
if ($ExportPg) {
    Invoke-Step "export pg ust-veri (dry run)" @("mutalaa", "export", "pg", "--source", "tanzil-ust-veri", "--dry-run")
    Invoke-Step "export pg ust-veri" @("mutalaa", "export", "pg", "--source", "tanzil-ust-veri")
}
Invoke-Step "test vectors check" @("mutalaa", "export", "test-vectors", "--tanzil-ornekleri", "--check")

$pytestArgs = @("pytest", "-m", "degismezlik", "-rs", "-q", "-p", "no:cacheprovider")
if (-not $ExportPg) {
    $pytestArgs += @("-k", "not postgresql")
}
$onceki = $env:MUTALAA_DEGISMEZLIK_ZORUNLU
$env:MUTALAA_DEGISMEZLIK_ZORUNLU = "1"
try {
    Invoke-Step "immutability tests" $pytestArgs
}
finally {
    if ($null -eq $onceki) {
        Remove-Item Env:MUTALAA_DEGISMEZLIK_ZORUNLU -ErrorAction SilentlyContinue
    }
    else {
        $env:MUTALAA_DEGISMEZLIK_ZORUNLU = $onceki
    }
}
Write-Output "nightly: all steps passed"
