param([switch]$Build)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$args = @('-p', 'expense_splitter_local', '-f', (Join-Path $root 'docker-compose.yml'), 'up', '-d')
if ($Build) { $args += '--build' }
docker compose @args
Write-Host 'Local mode: http://localhost:5173'
Write-Host 'Local API:  http://localhost:8000/docs'
