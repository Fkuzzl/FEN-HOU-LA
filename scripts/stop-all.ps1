$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
docker compose -p expense_splitter_local -f (Join-Path $root 'docker-compose.yml') down
docker compose -p expense_splitter_public -f (Join-Path $root 'docker-compose.yml') -f (Join-Path $root 'docker-compose.public.yml') down
Write-Host 'Both modes stopped. Database volumes were preserved.'
