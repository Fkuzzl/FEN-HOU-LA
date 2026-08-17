param(
  [string]$PublicOrigin = $(if ($env:PUBLIC_ORIGIN) { $env:PUBLIC_ORIGIN } else { 'http://localhost:55173' }),
  [string]$TrustedHosts = $(if ($env:PUBLIC_TRUSTED_HOSTS) { $env:PUBLIC_TRUSTED_HOSTS } else { 'localhost,127.0.0.1' }),
  [switch]$Build
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$docker = (Get-Command docker -ErrorAction SilentlyContinue).Source
if (-not $docker) { $docker = @('C:\Program Files\Docker\Docker\resources\bin\docker.exe', "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1 }
if (-not $docker) { throw 'Docker CLI was not found. Start Docker Desktop or add docker.exe to PATH.' }
$envFile = Join-Path $root '.env.public'
if (-not (Test-Path $envFile)) { throw 'Create .env.public from .env.public.example before starting public mode. Public mode never reads the local .env file.' }
if (-not $env:PUBLIC_JWT_SECRET) { $env:PUBLIC_JWT_SECRET = ((New-Guid).Guid + (New-Guid).Guid) }
$env:PUBLIC_ORIGIN = $PublicOrigin
# Docker's internal health probe uses localhost; keep it trusted alongside the
# externally configured hostname without requiring users to remember it.
$trustedHostValues = @($TrustedHosts -split ',') + @('localhost', '127.0.0.1')
$env:PUBLIC_TRUSTED_HOSTS = ($trustedHostValues | ForEach-Object { $_.Trim() } | Where-Object { $_ } | Select-Object -Unique) -join ','
$env:PUBLIC_COOKIE_SECURE = if ($PublicOrigin.StartsWith('https://')) { 'true' } else { 'false' }
$args = @('--env-file', $envFile, '-p', 'expense_splitter_public', '-f', (Join-Path $root 'docker-compose.yml'), '-f', (Join-Path $root 'docker-compose.public.yml'), 'up', '-d')
if ($Build) { $args += '--build' }
& $docker compose @args
Write-Host "Public-demo mode: $PublicOrigin"
Write-Host 'Local binding:    http://localhost:55173'
Write-Host 'Database volume:  expense_splitter_public_v2_db'
Write-Host 'The public origin is only reachable through your separately configured tunnel or proxy.'
