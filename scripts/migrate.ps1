param(
    [switch]$ResetPublicSchema = $false
)

$ErrorActionPreference = "Stop"

function Run-Step {
    param(
        [Parameter(Mandatory = $true)][string]$Title,
        [Parameter(Mandatory = $true)][scriptblock]$Action
    )
    Write-Host ""
    Write-Host "==> $Title" -ForegroundColor Cyan
    & $Action
}

Write-Host "SmartPantry DB migration helper" -ForegroundColor Green
Write-Host "Working dir: $(Get-Location)"

Run-Step -Title "Starting required services (db, app)" -Action {
    docker compose up -d db app | Out-Host
}

if ($ResetPublicSchema) {
    Run-Step -Title "Resetting public schema (DESTRUCTIVE)" -Action {
        docker compose exec db psql -U user -d smartpantry -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" | Out-Host
    }
}

$alembicVersionExists = (
    docker compose exec db psql -U user -d smartpantry -t -A -c "SELECT to_regclass('public.alembic_version') IS NOT NULL;"
).Trim()

if ($alembicVersionExists -eq "t") {
    Run-Step -Title "Running normal Alembic upgrade (tracked database)" -Action {
        docker compose exec app alembic upgrade head | Out-Host
    }
} else {
    Run-Step -Title "Bootstrapping via offline SQL pipe (alembic_version missing)" -Action {
        $sql = docker compose exec app alembic upgrade head --sql
        $sql | docker compose exec -T db psql -U user -d smartpantry | Out-Host
    }
}

Run-Step -Title "Verifying migrated revision" -Action {
    docker compose exec db psql -U user -d smartpantry -c "SELECT version_num FROM alembic_version;" | Out-Host
}

Run-Step -Title "Verifying generated tables" -Action {
    docker compose exec db psql -U user -d smartpantry -c "\dt" | Out-Host
}

Write-Host ""
Write-Host "Migration completed." -ForegroundColor Green
Write-Host "Usage:"
Write-Host "  .\scripts\migrate.ps1                  # normal migrate"
Write-Host "  .\scripts\migrate.ps1 -ResetPublicSchema  # reset + migrate (dev only)"
