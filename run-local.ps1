# Runs the whole stack on this machine: the five AWS services from infra/docker-compose.yml
# (api, worker, cpp-core, ml, audio-producer), MySQL in place of RDS, LocalStack in place of S3
# and SQS, and the Next.js frontend on http://localhost:3000.
#
#   .\run-local.ps1              build, start, then run the frontend (Ctrl+C stops only the frontend)
#   .\run-local.ps1 -NoFrontend  start only the backend
#   .\run-local.ps1 -Logs        follow the backend logs
#   .\run-local.ps1 -Down        stop everything and delete the local data
#
# Data lasts while the containers run. LocalStack keeps S3 and SQS in memory and MySQL uses an
# unnamed volume, so -Down starts the next run empty.
param(
    [switch]$Down,
    [switch]$Logs,
    [switch]$NoFrontend
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

$compose = @("compose", "-f", (Join-Path $root "infra/docker-compose.yml"))

function Wait-Docker {
    docker version --format "{{.Server.Version}}" *> $null
    if ($LASTEXITCODE -eq 0) { return }
    $desktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (-not (Test-Path $desktop)) { throw "Docker isn't running and Docker Desktop wasn't found." }
    Write-Host "Starting Docker Desktop..."
    Start-Process $desktop
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep 5
        docker version --format "{{.Server.Version}}" *> $null
        if ($LASTEXITCODE -eq 0) { return }
    }
    throw "Docker didn't start within 5 minutes."
}

Wait-Docker

if ($Down) {
    docker @compose down -v
    exit $LASTEXITCODE
}
if ($Logs) {
    docker @compose logs -f --tail 100
    exit $LASTEXITCODE
}

Write-Host "Building and starting the backend (the first build takes a while)..."
docker @compose up --build -d
if ($LASTEXITCODE -ne 0) { throw "docker compose up failed." }

# The api only starts after migrate finishes, so /health answering means MySQL, the migration
# and the api are all up.
Write-Host "Waiting for the API on http://localhost:4000/health ..."
$healthy = $false
for ($i = 0; $i -lt 60; $i++) {
    try {
        Invoke-RestMethod http://localhost:4000/health -TimeoutSec 3 | Out-Null
        $healthy = $true
        break
    } catch { Start-Sleep 3 }
}
if (-not $healthy) {
    docker @compose ps
    throw "The API didn't become healthy. Check: .\run-local.ps1 -Logs"
}
docker @compose ps
Write-Host "Backend is up. GraphQL: http://localhost:4000/graphql"

if ($NoFrontend) { exit 0 }

$frontend = Join-Path $root "frontend"
if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "Installing frontend packages..."
    npm --prefix $frontend install
}
# A process variable wins over the .env files, so the dev server always uses the local API.
$env:NEXT_PUBLIC_GRAPHQL_ENDPOINT = "http://localhost:4000/graphql"
Write-Host "Starting the frontend on http://localhost:3000 (Ctrl+C stops it; the backend keeps running)"
npm --prefix $frontend run dev
