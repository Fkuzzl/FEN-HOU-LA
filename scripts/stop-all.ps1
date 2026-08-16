$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$docker = (Get-Command docker -ErrorAction SilentlyContinue).Source
if (-not $docker) { $docker = @('C:\Program Files\Docker\Docker\resources\bin\docker.exe', "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1 }
if (-not $docker) { throw 'Docker CLI was not found. Start Docker Desktop or add docker.exe to PATH.' }
& $docker compose -p expense_splitter_local -f (Join-Path $root 'docker-compose.yml') down
& $docker compose -p expense_splitter_public -f (Join-Path $root 'docker-compose.yml') -f (Join-Path $root 'docker-compose.public.yml') down
Write-Host 'Both modes stopped. Database volumes were preserved.'
