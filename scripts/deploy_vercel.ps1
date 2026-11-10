# Deploy the API to Vercel (project kolbe-ir-api -> https://kolbe-ir-api.vercel.app).
# Builds a clean bundle in %TEMP%: app/, requirements (without test/dev tools), vercel.json, and the
# seed photos under public/uploads so Vercel's CDN serves them at /uploads/seed/...
# Requires the Vercel CLI, logged in (npm i -g vercel; vercel login).
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$out = Join-Path $env:TEMP "kolbe-api-deploy"
if (Test-Path $out) { Remove-Item $out -Recurse -Force }
New-Item -ItemType Directory -Force "$out\public\uploads", "$out\.vercel" | Out-Null

Copy-Item "$root\app" "$out\app" -Recurse
Get-ChildItem "$out\app" -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
Copy-Item "$root\uploads\seed" "$out\public\uploads\seed" -Recurse
$reqs = Get-Content "$root\requirements.txt" | Where-Object { $_ -notmatch '^(pytest|httpx|uvicorn)' }
# Without a BOM: pip / uv reject the one Windows PowerShell's -Encoding utf8 writes
[IO.File]::WriteAllLines("$out\requirements.txt", [string[]]$reqs, (New-Object Text.UTF8Encoding $false))
Copy-Item "$root\deploy\vercel.json" "$out\vercel.json"
Copy-Item "$root\deploy\project.json" "$out\.vercel\project.json"

Push-Location $out
# The CLI prints progress on stderr; with "Stop" Windows PowerShell 5.1 would treat that as an error
$ErrorActionPreference = "Continue"
try { vercel deploy --prod --yes; if ($LASTEXITCODE) { exit $LASTEXITCODE } } finally { Pop-Location }
