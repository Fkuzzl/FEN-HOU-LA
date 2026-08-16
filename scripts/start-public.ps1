param(
  [string]$PublicOrigin = $(if ($env:PUBLIC_ORIGIN) { $env:PUBLIC_ORIGIN } else { 'http://localhost:55173' }),
  [string]$TrustedHosts = $(if ($env:PUBLIC_TRUSTED_HOSTS) { $env:PUBLIC_TRUSTED_HOSTS } else { 'localhost,127.0.0.1' }),
  [switch]$Build
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not $env:PUBLIC_JWT_SECRET) { $env:PUBLIC_JWT_SECRET = ((New-Guid).Guid + (New-Guid).Guid) }
$env:PUBLIC_ORIGIN = $PublicOrigin
$env:PUBLIC_TRUSTED_HOSTS = $TrustedHosts
$env:PUBLIC_COOKIE_SECURE = if ($PublicOrigin.StartsWith('https://')) { 'true' } else { 'false' }
$args = @('-p', 'expense_splitter_public', '-f', (Join-Path $root 'docker-compose.yml'), '-f', (Join-Path $root 'docker-compose.public.yml'), 'up', '-d')
if ($Build) { $args += '--build' }
docker compose @args
Write-Host "Public-demo mode: $PublicOrigin"
Write-Host 'Local binding:    http://localhost:55173'
Write-Host 'Database volume:  expense_splitter_public_v2_db'
Write-Host 'The public origin is only reachable through your separately configured tunnel or proxy.'
