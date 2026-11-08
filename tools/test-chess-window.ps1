# Windows end-to-end smoke: launch the actual game, observe its HWND,
# request a graceful close, and verify no runtime errors were emitted.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class BeaconChessWindowProbe {
    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern IntPtr FindWindow(string className, string windowName);
    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool PostMessage(IntPtr hwnd, uint message, IntPtr wparam, IntPtr lparam);
}
"@
$log = Join-Path $env:TEMP "beacon-chess-smoke-out.txt"
$errors = Join-Path $env:TEMP "beacon-chess-smoke-err.txt"
$process = $null
try {
    $launcher = Join-Path $root "beacon.ps1"
    $process = Start-Process -FilePath "pwsh" -ArgumentList @(
        "-NoProfile", "-File", $launcher, "examples/chess-ashen-crypt.beacon"
    ) -PassThru -RedirectStandardOutput $log -RedirectStandardError $errors
    $handle = [IntPtr]::Zero
    for ($i = 0; $i -lt 120; $i++) {
        # Process.MainWindowHandle resolves correctly on hosted Windows runners,
        # including windows whose title lookup fails through FindWindow.
        $gameProcess = Get-Process -Name dotnet -ErrorAction SilentlyContinue |
            Where-Object { $_.MainWindowTitle -eq "Beacon Chess" } |
            Select-Object -First 1
        if ($null -ne $gameProcess) { $handle = $gameProcess.MainWindowHandle }
        if ($handle -ne [IntPtr]::Zero) { break }
        if ($process.HasExited) { break }
        Start-Sleep -Milliseconds 250
    }
    if ($handle -eq [IntPtr]::Zero) {
        Write-Host "Launcher exited: $($process.HasExited)"
        Get-Process | Where-Object { $_.MainWindowTitle } | Select-Object Id,ProcessName,MainWindowTitle | Format-Table | Out-String | Write-Host
        Get-Process -Name dotnet -ErrorAction SilentlyContinue | Select-Object Id,CPU,StartTime | Format-Table | Out-String | Write-Host
        throw "Chess window never appeared. Output: $(Get-Content $log -Raw) Errors: $(Get-Content $errors -Raw)"
    }
    if (-not [BeaconChessWindowProbe]::PostMessage($handle, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero)) {
        throw "Failed to send close event to the Chess window"
    }
    if (-not $process.WaitForExit(15000)) { throw "Chess process did not exit after window close" }
    if ($process.ExitCode -ne 0) { throw "Chess exited $($process.ExitCode). Output: $(Get-Content $log -Raw) Errors: $(Get-Content $errors -Raw)" }
    Write-Host "Beacon Chess opened a native game window and exited cleanly."
}
finally {
    if ($null -ne $process -and -not $process.HasExited) { Stop-Process -Id $process.Id -Force }
    Pop-Location
}
