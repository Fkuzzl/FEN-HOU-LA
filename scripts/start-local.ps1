param([switch]$Build)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$docker = (Get-Command docker -ErrorAction SilentlyContinue).Source
if (-not $docker) { $docker = @('C:\Program Files\Docker\Docker\resources\bin\docker.exe', "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1 }
if (-not $docker) { throw 'Docker CLI was not found. Start Docker Desktop or add docker.exe to PATH.' }
$envFile = if (Test-Path (Join-Path $root '.env.local')) { Join-Path $root '.env.local' } elseif (Test-Path (Join-Path $root '.env')) { Join-Path $root '.env' } else { throw 'Create .env.local from .env.example before starting local mode.' }
$args = @('--env-file', $envFile, '-p', 'expense_splitter_local', '-f', (Join-Path $root 'docker-compose.yml'), 'up', '-d')
if ($Build) { $args += '--build' }
& $docker compose @args
Write-Host 'Local mode: http://localhost:5173'
Write-Host 'Local API:  http://localhost:8000/docs'
