# Windows end-to-end smoke: launch the actual game, observe its HWND,
# request a graceful close, and verify no runtime errors were emitted.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class BeaconRpgWindowProbe {
    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern IntPtr FindWindow(string className, string windowName);
    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool PostMessage(IntPtr hwnd, uint message, IntPtr wparam, IntPtr lparam);
}
"@
$log = Join-Path $env:TEMP "beacon-rpg-smoke-out.txt"
$errors = Join-Path $env:TEMP "beacon-rpg-smoke-err.txt"
$process = $null
try {
    $launcher = Join-Path $root "beacon.ps1"
    $process = Start-Process -FilePath "pwsh" -ArgumentList @(
        "-NoProfile", "-File", $launcher, "examples/rpg-ashen-crypt.beacon"
    ) -PassThru -RedirectStandardOutput $log -RedirectStandardError $errors
    $handle = [IntPtr]::Zero
    for ($i = 0; $i -lt 120; $i++) {
        $handle = [BeaconRpgWindowProbe]::FindWindow($null, "The Ashen Crypt - Beacon RPG")
        if ($handle -ne [IntPtr]::Zero) { break }
        if ($process.HasExited) { break }
        Start-Sleep -Milliseconds 250
    }
    if ($handle -eq [IntPtr]::Zero) { throw "RPG window never appeared. Output: $(Get-Content $log -Raw) Errors: $(Get-Content $errors -Raw)" }
    if (-not [BeaconRpgWindowProbe]::PostMessage($handle, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero)) {
        throw "Failed to send close event to the RPG window"
    }
    if (-not $process.WaitForExit(15000)) { throw "RPG process did not exit after window close" }
    if ($process.ExitCode -ne 0) { throw "RPG exited $($process.ExitCode). Output: $(Get-Content $log -Raw) Errors: $(Get-Content $errors -Raw)" }
    Write-Host "The Ashen Crypt opened a native game window and exited cleanly."
}
finally {
    if ($null -ne $process -and -not $process.HasExited) { Stop-Process -Id $process.Id -Force }
    Pop-Location
}
