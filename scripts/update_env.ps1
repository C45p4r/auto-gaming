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
  "CAPTURE_BACKEND"        = "auto";
  "INPUT_BACKEND"          = "auto";
  "WINDOW_TITLE_HINT"      = "Epic\s*Seven|FRI3ZD";
  "WINDOW_ENFORCE_TOPMOST" = "true";
  "WINDOW_LEFT"            = "100";
  "WINDOW_TOP"             = "100";
  "WINDOW_CLIENT_WIDTH"    = "1280";
  "WINDOW_CLIENT_HEIGHT"   = "720";
  "INPUT_BASE_WIDTH"       = "1280";
  "INPUT_BASE_HEIGHT"      = "720";
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

