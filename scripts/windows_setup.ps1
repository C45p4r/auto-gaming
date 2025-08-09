Param(
  [string]$EnvFile = ".env"
)

Write-Host "Setting up auto-gaming for Windows..." -ForegroundColor Cyan

if (-Not (Test-Path -Path ".venv")) {
  python -m venv .venv
}

& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

if (-Not (Test-Path -Path $EnvFile)) {
  Copy-Item env.example $EnvFile
}

Write-Host "Done. Start server: `n  .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --reload" -ForegroundColor Green

