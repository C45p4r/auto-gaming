Param(
  [string]$EnvFile = ".env"
)

if (-not (Test-Path -Path $EnvFile)) {
  if (Test-Path -Path "env.example") {
    Copy-Item "env.example" $EnvFile
  } else {
    New-Item -ItemType File -Path $EnvFile | Out-Null
  }
}

$content = Get-Content -Raw -ErrorAction SilentlyContinue $EnvFile
if ($null -eq $content) { $content = "" }

$kv = @{
  "CAPTURE_BACKEND"        = "window";
  "INPUT_BACKEND"          = "window";
  "WINDOW_TITLE_HINT"      = "Google Play Games|Epic Seven|Epic 7|Epic Seven - FRl3ZD";
  "WINDOW_ENFORCE_TOPMOST" = "true";
  "WINDOW_LEFT"            = "82";
  "WINDOW_TOP"             = "80";
  "WINDOW_CLIENT_WIDTH"    = "882";
  "WINDOW_CLIENT_HEIGHT"   = "496";
  "INPUT_BASE_WIDTH"       = "882";
  "INPUT_BASE_HEIGHT"      = "496";
  "INPUT_EXCLUDE_BOTTOM_PX"= "40";
  "CAPTURE_FPS"            = "2";
  "OCR_SCALE"              = "3.0";
  "OCR_PSM"                = "11";
  "OCR_ENGINES"            = "paddle,tesseract_batched,tesseract";
  "RL_ENABLED"             = "true";
  "RL_METHOD"              = "bandit";
  "RL_EPS_START"           = "0.35";
  "RL_EPS_END"             = "0.15";
}

foreach ($k in $kv.Keys) {
  $line = "$k=" + $kv[$k]
  $pattern = "(?m)^" + [regex]::Escape($k) + "=.*"
  if ($content -match $pattern) {
    $content = [regex]::Replace($content, $pattern, $line)
  } else {
    if ($content -and -not $content.EndsWith("`n")) { $content += "`r`n" }
    $content += $line + "`r`n"
  }
}

Set-Content -Path $EnvFile -Value $content -Encoding UTF8
Write-Host "Updated $EnvFile with emulator window settings."

