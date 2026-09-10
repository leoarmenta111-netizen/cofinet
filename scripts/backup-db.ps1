param(
    [ValidateSet("dev", "qa", "prod")]
    [string]$Environment = "qa"
)
$ErrorActionPreference = "Stop"

$settings = @{
    dev  = @{ Env = ".env.local"; Overlay = "docker-compose.dev.yml" }
    qa   = @{ Env = ".env.qa"; Overlay = "docker-compose.qa.yml" }
    prod = @{ Env = ".env.production"; Overlay = "docker-compose.prod.yml" }
}[$Environment]
$timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$containerDump = "/tmp/cofinet-$Environment-$timestamp.dump"
$hostDump = Join-Path "backups" "cofinet-$Environment-$timestamp.dump"
New-Item -ItemType Directory -Force -Path "backups" | Out-Null
$compose = @("compose", "--env-file", $settings.Env, "-f", "docker-compose.yml", "-f", $settings.Overlay)

& docker @compose exec -T postgres sh -c 'pg_dump -Fc --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$1"' sh $containerDump
if ($LASTEXITCODE -ne 0) { throw "pg_dump failed." }
& docker @compose cp "postgres:$containerDump" $hostDump
if ($LASTEXITCODE -ne 0) { throw "Copying the dump failed." }
& docker @compose exec -T postgres rm -f $containerDump
Write-Output "Backup created: $hostDump"

