$ErrorActionPreference = 'Stop'
param(
  [switch]$Foreground
)

$root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $root

# Activate venv
. .\.venv\Scripts\Activate.ps1

# Required env for Windows emulator (updated to match new .env)
$env:TESSERACT_CMD = 'C:\Program Files\Tesseract-OCR\tesseract.exe'
$env:TESSDATA_PREFIX = 'C:\Program Files\Tesseract-OCR\tessdata'
$env:OCR_LANGUAGE = 'eng'
$env:OCR_SCALE = '3.0'
$env:OCR_PSM = '11'
$env:OCR_ENGINES = 'paddle,tesseract_batched,tesseract'
$env:CAPTURE_FPS = '2'
$env:CAPTURE_BACKEND = 'window'
$env:INPUT_BACKEND = 'window'
$env:WINDOW_TITLE_HINT = 'Google Play Games|Epic Seven|Epic 7|Epic Seven - FRl3ZD'
$env:WINDOW_ENFORCE_TOPMOST = 'true'
$env:WINDOW_FORCE_FOREGROUND = 'true'
$env:WINDOW_LEFT = '82'
$env:WINDOW_TOP = '80'
$env:WINDOW_CLIENT_WIDTH = '882'
$env:WINDOW_CLIENT_HEIGHT = '496'
$env:INPUT_BASE_WIDTH = '882'
$env:INPUT_BASE_HEIGHT = '496'
$env:INPUT_EXCLUDE_BOTTOM_PX = '40'
$env:RL_ENABLED = 'true'
$env:RL_METHOD = 'bandit'
$env:RL_EPS_START = '0.35'
$env:RL_EPS_END = '0.15'

if ($Foreground) {
  uvicorn app.main:app --host 127.0.0.1 --port 8000
} else {
  Start-Process -WindowStyle Hidden powershell -ArgumentList @(
    '-NoProfile','-ExecutionPolicy','Bypass','-Command',
    "Set-Location $root; . .\\.venv\\Scripts\\Activate.ps1; ``
    $env:TESSERACT_CMD='C:\\Program Files\\Tesseract-OCR\\tesseract.exe'; ``
    $env:TESSDATA_PREFIX='C:\\Program Files\\Tesseract-OCR\\tessdata'; ``
    $env:OCR_LANGUAGE='eng'; ``
    $env:OCR_SCALE='3.0'; ``
    $env:OCR_PSM='11'; ``
    $env:OCR_ENGINES='paddle,tesseract_batched,tesseract'; ``
    $env:CAPTURE_FPS='2'; ``
    $env:CAPTURE_BACKEND='window'; ``
    $env:INPUT_BACKEND='window'; ``
    $env:WINDOW_TITLE_HINT='Google Play Games|Epic Seven|Epic 7|Epic Seven - FRl3ZD'; ``
    $env:WINDOW_ENFORCE_TOPMOST='true'; ``
    $env:WINDOW_FORCE_FOREGROUND='true'; ``
    $env:WINDOW_LEFT='82'; ``
    $env:WINDOW_TOP='80'; ``
    $env:WINDOW_CLIENT_WIDTH='882'; ``
    $env:WINDOW_CLIENT_HEIGHT='496'; ``
    $env:INPUT_BASE_WIDTH='882'; ``
    $env:INPUT_BASE_HEIGHT='496'; ``
    $env:INPUT_EXCLUDE_BOTTOM_PX='40'; ``
    $env:RL_ENABLED='true'; ``
    $env:RL_METHOD='bandit'; ``
    $env:RL_EPS_START='0.35'; ``
    $env:RL_EPS_END='0.15'; ``
    uvicorn app.main:app --host 127.0.0.1 --port 8000"
  ) | Out-Null
  Write-Host 'Backend started in background.'
}


