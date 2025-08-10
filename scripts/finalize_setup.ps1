Param(
  [string]$ProjectRoot = (Resolve-Path ".").Path,
  [string]$TesseractDir = $null
)

Set-Location $ProjectRoot

# Activate venv
$venvActivate = Join-Path $ProjectRoot ".venv/Scripts/Activate.ps1"
if (-not (Test-Path $venvActivate)) { Write-Error ".venv not found"; exit 1 }
. $venvActivate

# Locate Tesseract if not provided
if (-not $TesseractDir) {
  $candidates = @(
    "C:\\Program Files\\Tesseract-OCR",
    "C:\\Program Files (x86)\\Tesseract-OCR"
  )
  foreach ($c in $candidates) {
    if (Test-Path (Join-Path $c "tesseract.exe")) { $TesseractDir = $c; break }
  }
}
if (-not $TesseractDir -or -not (Test-Path (Join-Path $TesseractDir "tesseract.exe"))) {
  Write-Error "Tesseract not found. Install it or pass -TesseractDir 'C:\\Path\\to\\Tesseract-OCR'"
  exit 2
}

# Session env
if (-not (($env:PATH -split ";") -contains $TesseractDir)) { $env:PATH = "$TesseractDir;$env:PATH" }
$env:TESSDATA_PREFIX = (Join-Path $TesseractDir "tessdata")

# Persist for user (append dir if absent)
$userPath = [Environment]::GetEnvironmentVariable("PATH","User")
if (-not (($userPath -split ";") -contains $TesseractDir)) {
  [Environment]::SetEnvironmentVariable("PATH", ($userPath + ";" + $TesseractDir), "User")
}
[Environment]::SetEnvironmentVariable("TESSDATA_PREFIX", $env:TESSDATA_PREFIX, "User")

# Update .env with window/input settings and broader title hint
$envFile = Join-Path $ProjectRoot ".env"
if (-not (Test-Path $envFile)) { if (Test-Path "env.example") { Copy-Item env.example $envFile } else { New-Item -ItemType File -Path $envFile | Out-Null } }
$content = Get-Content -Raw $envFile
$kv = @{
  "CAPTURE_BACKEND"       = "auto";
  "INPUT_BACKEND"         = "auto";
  "WINDOW_TITLE_HINT"     = "Epic\\s*Seven|Seven|FRI3ZD";
  "WINDOW_ENFORCE_TOPMOST"= "true";
  "WINDOW_LEFT"           = "100";
  "WINDOW_TOP"            = "100";
  "WINDOW_CLIENT_WIDTH"   = "1280";
  "WINDOW_CLIENT_HEIGHT"  = "720";
  "INPUT_BASE_WIDTH"      = "1280";
  "INPUT_BASE_HEIGHT"     = "720";
}
foreach ($k in $kv.Keys) {
  $line = "$k=" + $kv[$k]
  $pattern = "(?m)^" + [regex]::Escape($k) + "=.*"
  if ($content -match $pattern) { $content = [regex]::Replace($content, $pattern, $line) }
  else { if ($content -and -not $content.EndsWith("`n")) { $content += "`r`n" }; $content += $line + "`r`n" }
}
Set-Content -Path $envFile -Value $content -Encoding UTF8

# Start backend if not listening
$ok = $false
try { $resp = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/health' -TimeoutSec 2; if ($resp.status -eq 'ok') { $ok = $true } } catch {}
if (-not $ok) {
  Start-Process -WindowStyle Hidden -FilePath (Join-Path $ProjectRoot ".venv/Scripts/python.exe") -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000') | Out-Null
  Start-Sleep 3
}

# Verify health
$resp = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/health' -TimeoutSec 5
if ($resp.status -ne 'ok') { Write-Error "Backend health failed"; exit 3 }

# Capture one frame
python -m app.cli capture --ensure-window --output-dir captures

Write-Host "Finalize setup complete. UI: http://localhost:5173  | Backend: http://127.0.0.1:8000/health"

