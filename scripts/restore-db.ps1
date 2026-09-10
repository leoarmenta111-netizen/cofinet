param(
    [Parameter(Mandatory)]
    [ValidateSet("dev", "qa")]
    [string]$Environment,
    [Parameter(Mandatory)]
    [string]$DumpPath,
    [switch]$ConfirmRestore
)
$ErrorActionPreference = "Stop"
if (-not $ConfirmRestore) { throw "Restore replaces data. Re-run with -ConfirmRestore." }
$resolvedDump = (Resolve-Path -LiteralPath $DumpPath).Path
$settings = if ($Environment -eq "dev") {
    @{ Env = ".env.local"; Overlay = "docker-compose.dev.yml" }
} else {
    @{ Env = ".env.qa"; Overlay = "docker-compose.qa.yml" }
}
$extension = [IO.Path]::GetExtension($resolvedDump).TrimStart(".")
$containerDump = "/tmp/cofinet-restore-$([guid]::NewGuid().ToString('N')).$extension"
$compose = @("compose", "--env-file", $settings.Env, "-f", "docker-compose.yml", "-f", $settings.Overlay)

& docker @compose stop nginx backend 2>$null
& docker @compose up -d postgres
if ($LASTEXITCODE -ne 0) { throw "PostgreSQL failed to start." }
& docker @compose cp $resolvedDump "postgres:$containerDump"
if ($LASTEXITCODE -ne 0) { throw "Copying the dump failed." }
& docker @compose exec -T postgres sh -c 'dropdb --if-exists --force -U "$POSTGRES_USER" "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" "$POSTGRES_DB"'
if ($LASTEXITCODE -ne 0) { throw "Recreating the target database failed." }
if ($extension -in @("dump", "backup")) {
    & docker @compose exec -T postgres sh -c 'pg_restore --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB" "$1"' sh $containerDump
} else {
    & docker @compose exec -T postgres sh -c 'psql -v ON_ERROR_STOP=1 --single-transaction -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$1"' sh $containerDump
}
if ($LASTEXITCODE -ne 0) { throw "Restore failed; inspect PostgreSQL output." }
& docker @compose exec -T postgres rm -f $containerDump
Write-Output "Restore completed in the isolated $Environment database."
