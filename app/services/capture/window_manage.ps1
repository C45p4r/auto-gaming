Param([string]$TitleHint)
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WinApi {
  public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder text, int count);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
}
"@
$found = [IntPtr]::Zero
[WinApi+EnumWindowsProc] $cb = {
  param([IntPtr] $h,[IntPtr] $l)
  if (-not [WinApi]::IsWindowVisible($h)) { return $true }
  $sb = New-Object System.Text.StringBuilder 512
  [void][WinApi]::GetWindowText($h,$sb,512)
  $t = $sb.ToString()
  if ($t -and ($t -match $TitleHint)) { $script:found = $h; return $false }
  return $true
}
[WinApi]::EnumWindows($cb, [IntPtr]::Zero) | Out-Null
if ($found -ne [IntPtr]::Zero) { [void][WinApi]::SetForegroundWindow($found) }
