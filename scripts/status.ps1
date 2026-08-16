$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Write-Host 'LOCAL'
docker compose -p expense_splitter_local -f (Join-Path $root 'docker-compose.yml') ps
Write-Host 'PUBLIC-DEMO'
docker compose -p expense_splitter_public -f (Join-Path $root 'docker-compose.yml') -f (Join-Path $root 'docker-compose.public.yml') ps
