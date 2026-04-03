# RentalAI — 静态前端构建（inject API base meta）。同源浏览请用 start_backend.ps1。
# 分域预演前可设置: $env:RENTALAI_API_BASE = 'https://你的API根'
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot 'web_public')
npm run build
Write-Host 'Build OK. Same-origin: run .\start_backend.ps1 then open http://127.0.0.1:8000/ (or your PORT).'
