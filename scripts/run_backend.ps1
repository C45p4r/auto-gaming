$ErrorActionPreference = 'Stop'
param(
  [switch]$Foreground
)

$root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $root

# Activate venv
. .\.venv\Scripts\Activate.ps1

# Required env for Windows emulator
$env:TESSERACT_CMD = 'C:\Program Files\Tesseract-OCR\tesseract.exe'
$env:TESSDATA_PREFIX = 'C:\Program Files\Tesseract-OCR\tessdata'
$env:OCR_LANGUAGE = 'eng'
$env:CAPTURE_BACKEND = 'window'
$env:INPUT_BACKEND = 'window'
$env:WINDOW_TITLE_HINT = 'Epic Seven|Google Play Games'
$env:WINDOW_ENFORCE_TOPMOST = 'true'
$env:WINDOW_FORCE_FOREGROUND = 'true'
$env:INPUT_BASE_WIDTH = '1280'
$env:INPUT_BASE_HEIGHT = '720'

if ($Foreground) {
  uvicorn app.main:app --host 127.0.0.1 --port 8000
} else {
  Start-Process -WindowStyle Hidden powershell -ArgumentList @(
    '-NoProfile','-ExecutionPolicy','Bypass','-Command',
    "Set-Location $root; . .\\.venv\\Scripts\\Activate.ps1; `
    $env:TESSERACT_CMD='C:\\Program Files\\Tesseract-OCR\\tesseract.exe'; `
    $env:TESSDATA_PREFIX='C:\\Program Files\\Tesseract-OCR\\tessdata'; `
    $env:OCR_LANGUAGE='eng'; `
    $env:CAPTURE_BACKEND='window'; `
    $env:INPUT_BACKEND='window'; `
    $env:WINDOW_TITLE_HINT='Epic Seven|Google Play Games'; `
    $env:WINDOW_ENFORCE_TOPMOST='true'; `
    $env:WINDOW_FORCE_FOREGROUND='true'; `
    $env:INPUT_BASE_WIDTH='1280'; `
    $env:INPUT_BASE_HEIGHT='720'; `
    uvicorn app.main:app --host 127.0.0.1 --port 8000"
  ) | Out-Null
  Write-Host 'Backend started in background.'
}


