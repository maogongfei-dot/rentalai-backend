# RentalAI — 读取 .env 中的 HOST/PORT，启动 uvicorn app:app（工作目录：rental_app）
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$bindHost = '0.0.0.0'
$bindPort = '8000'
$envFile = Join-Path $PSScriptRoot '.env'
if (Test-Path $envFile) {
    Get-Content $envFile -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if ($line -match '^\s*#' -or $line -eq '') { return }
        if ($line -match '^HOST=(.+)$') { $bindHost = $matches[1].Trim().Trim('"').Trim("'") }
        elseif ($line -match '^PORT=(.+)$') { $bindPort = $matches[1].Trim().Trim('"').Trim("'") }
    }
}

& uvicorn app:app --host $bindHost --port $bindPort
