$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$env:BEACON_HOME = $root

$seed = Join-Path $root 'bootstrap/stage0/Beacon.Compiler.dll'
$compiler = Join-Path $root 'compiler/compiler.beacon'
$launcher = Join-Path $root 'examples/inspect-launch-smoke.beacon'
$query = Join-Path $root 'examples/inspect-snapshot-smoke.beacon'

Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

public static class BeaconInspectionProbe
{
    public delegate bool EnumProc(IntPtr hwnd, IntPtr param);

    [DllImport("user32.dll")]
    public static extern bool EnumChildWindows(IntPtr parent, EnumProc callback, IntPtr data);

    [DllImport("user32.dll", CharSet = CharSet.Unicode, EntryPoint = "GetWindowTextW")]
    public static extern int GetText(IntPtr hwnd, StringBuilder text, int size);

    [DllImport("user32.dll", CharSet = CharSet.Unicode, EntryPoint = "GetClassNameW")]
    public static extern int GetClass(IntPtr hwnd, StringBuilder text, int size);

    [DllImport("user32.dll", EntryPoint = "SendMessageW")]
    public static extern IntPtr SendMessage(IntPtr hwnd, uint message, IntPtr wparam, IntPtr lparam);

    [DllImport("user32.dll", EntryPoint = "PostMessageW")]
    public static extern bool PostMessage(IntPtr hwnd, uint message, IntPtr wparam, IntPtr lparam);

    public static IntPtr IncrementButton(IntPtr parent)
    {
        IntPtr found = IntPtr.Zero;
        EnumProc callback = (child, data) =>
        {
            var type = new StringBuilder(80);
            GetClass(child, type, type.Capacity);
            var label = new StringBuilder(256);
            GetText(child, label, label.Capacity);
            if (type.ToString().Equals("Button", StringComparison.OrdinalIgnoreCase) &&
                label.ToString() == "Increment") found = child;
            return true;
        };
        EnumChildWindows(parent, callback, IntPtr.Zero);
        GC.KeepAlive(callback);
        return found;
    }
}
'@

$target = $null
try {
    $launchOutput = @(& dotnet $seed $compiler '--stage1-run' $launcher)
    if ($LASTEXITCODE -ne 0) { throw "inspect.launch failed: $($launchOutput -join '; ')" }
    $targetPid = [int]$launchOutput[-1]
    $target = Get-Process -Id $targetPid -ErrorAction Stop
    $env:BEACON_INSPECT_PID = "$targetPid"
    Write-Host "Inspection target PID: $targetPid"

    function Snapshot {
        $output = @(& dotnet $seed $compiler '--stage1-run' $query)
        if ($LASTEXITCODE -ne 0) { throw "Inspection client failed: $($output -join '; ')" }
        return ,$output
    }

    $first = @()
    $window = [IntPtr]::Zero
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        $target.Refresh()
        if ($target.HasExited) { throw "Target process exited before inspection (code $($target.ExitCode))" }
        $window = $target.MainWindowHandle
        $first = @(Snapshot)
        if ($window -ne [IntPtr]::Zero -and $first.Count -ge 3 -and
            $first[0] -eq 'true' -and $first[-1] -eq '0') { break }
        Start-Sleep -Milliseconds 250
    }
    if ($window -eq [IntPtr]::Zero) { throw 'Target window missing' }
    if ($first.Count -lt 3 -or $first[0] -ne 'true' -or $first[-1] -ne '0') {
        throw "Initial counter snapshot incorrect: $($first -join ', ')"
    }
    if ($first[1] -notlike '*inspector-target.beacon') { throw 'Snapshot missing target source path' }
    Write-Host "Initial live counter: $($first[-1])"

    $button = [BeaconInspectionProbe]::IncrementButton($window)
    if ($button -eq [IntPtr]::Zero) { throw "Target's Increment button missing" }
    [BeaconInspectionProbe]::SendMessage($button, 0x00F5, [IntPtr]::Zero, [IntPtr]::Zero) | Out-Null

    $second = @()
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        $second = @(Snapshot)
        if ($second.Count -ge 3 -and $second[0] -eq 'true' -and $second[-1] -eq '1') { break }
        Start-Sleep -Milliseconds 150
    }
    if ($second.Count -lt 3 -or $second[0] -ne 'true' -or $second[-1] -ne '1') {
        throw "Target variable did not change after native button press: $($second -join ', ')"
    }
    Write-Host 'Live counter updated: 0 -> 1'

    [BeaconInspectionProbe]::PostMessage($window, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero) | Out-Null
    if (-not $target.WaitForExit(5000)) { throw 'Target did not exit after window closed' }
    $last = @(Snapshot)
    if ($last.Count -eq 0 -or $last[0] -ne 'false') {
        throw "Inspection session remained attached after exit: $($last -join ', ')"
    }
    Write-Host 'Inspection process exited; disconnection detected safely.'
}
finally {
    if ($target -ne $null -and -not $target.HasExited) {
        Stop-Process -Id $target.Id -Force -ErrorAction SilentlyContinue
    }
}
