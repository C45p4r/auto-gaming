Param(
  [string]$ProjectRoot = (Split-Path -Parent $PSCommandPath)
)

Set-Location $ProjectRoot

# 1) Activate venv
$venvActivate = Join-Path $ProjectRoot ".venv/Scripts/Activate.ps1"
if (-not (Test-Path $venvActivate)) {
  Write-Error ".venv not found. Run: python -m venv .venv; then install requirements."
  exit 1
}
. $venvActivate

# 2) Ensure Tesseract is on PATH (session) and set TESSDATA_PREFIX
$tesseract = (Get-Command tesseract.exe -ErrorAction SilentlyContinue).Source
if (-not $tesseract) {
  $p1 = "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
  $p2 = "C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe"
  if (Test-Path $p1) { $tesseract = $p1 }
  elseif (Test-Path $p2) { $tesseract = $p2 }
}
if (-not $tesseract) {
  Write-Error "Tesseract not found. Install from https://github.com/UB-Mannheim/tesseract/wiki and re-run."
  exit 2
}
$tessDir = Split-Path -Parent $tesseract
if (-not ($env:PATH -split ";" | Where-Object { $_ -eq $tessDir })) {
  $env:PATH = "$tessDir;$env:PATH"
}
$env:TESSDATA_PREFIX = Join-Path $tessDir "tessdata"
[Environment]::SetEnvironmentVariable("TESSDATA_PREFIX", $env:TESSDATA_PREFIX, "User")
# Don't overwrite whole user PATH; append dir if missing
$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if (-not ($userPath -split ";" | Where-Object { $_ -eq $tessDir })) {
  [Environment]::SetEnvironmentVariable("PATH", ($userPath + ";" + $tessDir), "User")
}

# 3) Update .env with window/input settings
$updateEnv = Join-Path $ProjectRoot "scripts/update_env.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File $updateEnv | Out-Null

# 4) Start backend if not listening on 8000
$listening = $false
try {
  $conn = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction Stop
  if ($conn) { $listening = $true }
} catch {}
if (-not $listening) {
  Start-Process -WindowStyle Hidden -FilePath (Join-Path $ProjectRoot ".venv/Scripts/python.exe") -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000') | Out-Null
}

# 5) Wait for /health
for ($i=0; $i -lt 20; $i++) {
  Start-Sleep -Seconds 1
  try {
    $r = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/health' -TimeoutSec 2
    if ($r.status -eq 'ok') { break }
  } catch {}
}

# 6) Capture one frame with window enforcement
python -m app.cli capture --ensure-window --output-dir captures

# 7) Start agent via control endpoint
try { Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/telemetry/control/start' -TimeoutSec 3 | Out-Null } catch {}

Write-Host "Setup complete: Tesseract configured, env updated, backend healthy, one frame captured, agent started."

