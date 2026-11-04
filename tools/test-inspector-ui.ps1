$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$env:BEACON_HOME = $root
$seed = Join-Path $root 'bootstrap/stage0/Beacon.Compiler.dll'
$compiler = Join-Path $root 'compiler/compiler.beacon'
$source = Join-Path $root 'examples/inspector-ui.beacon'

Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

public static class BeaconInspectorUiProbe
{
    public delegate bool ChildCallback(IntPtr hwnd, IntPtr param);
    [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr parent, ChildCallback callback, IntPtr param);
    [DllImport("user32.dll", CharSet = CharSet.Unicode, EntryPoint = "GetClassNameW")]
    public static extern int GetClass(IntPtr hwnd, StringBuilder text, int size);
    [DllImport("user32.dll", CharSet = CharSet.Unicode, EntryPoint = "SendMessageW")]
    public static extern IntPtr GetText(IntPtr hwnd, uint message, IntPtr size, StringBuilder text);
    [DllImport("user32.dll", EntryPoint = "SendMessageW")]
    public static extern IntPtr Send(IntPtr hwnd, uint message, IntPtr a, IntPtr b);
    [DllImport("user32.dll", EntryPoint = "PostMessageW")]
    public static extern bool Post(IntPtr hwnd, uint message, IntPtr a, IntPtr b);

    public static string Label(IntPtr hwnd)
    {
        var text = new StringBuilder(32768);
        GetText(hwnd, 0x000D, (IntPtr)text.Capacity, text);
        return text.ToString();
    }

    public static IntPtr FindControl(IntPtr parent, string controlClass, string exactLabel)
    {
        IntPtr found = IntPtr.Zero;
        ChildCallback callback = (child, _) =>
        {
            var text = new StringBuilder(128);
            GetClass(child, text, text.Capacity);
            if (!text.ToString().Equals(controlClass, StringComparison.OrdinalIgnoreCase))
                return true;
            if (Label(child) == exactLabel) found = child;
            return true;
        };
        EnumChildWindows(parent, callback, IntPtr.Zero);
        GC.KeepAlive(callback);
        return found;
    }

    public static bool HasText(IntPtr parent, string controlClass, string fragment)
    {
        bool found = false;
        ChildCallback callback = (child, _) =>
        {
            var text = new StringBuilder(128);
            GetClass(child, text, text.Capacity);
            if (text.ToString().Equals(controlClass, StringComparison.OrdinalIgnoreCase) &&
                Label(child).Contains(fragment, StringComparison.Ordinal))
                found = true;
            return true;
        };
        EnumChildWindows(parent, callback, IntPtr.Zero);
        GC.KeepAlive(callback);
        return found;
    }
}
'@

$inspector = $null
$target = $null
try {
    $inspector = Start-Process -FilePath dotnet -ArgumentList @(
        $seed, $compiler, '--stage1-run', $source
    ) -WorkingDirectory $root -PassThru

    $window = [IntPtr]::Zero
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        Start-Sleep -Milliseconds 250
        $inspector.Refresh()
        if ($inspector.HasExited) { throw "Inspector exited early: $($inspector.ExitCode)" }
        $window = $inspector.MainWindowHandle
        if ($window -ne [IntPtr]::Zero) { break }
    }
    if ($window -eq [IntPtr]::Zero) { throw 'Inspector window did not appear' }

    $launch = [BeaconInspectorUiProbe]::FindControl($window, 'Button', 'Launch sample')
    if ($launch -eq [IntPtr]::Zero) { throw 'Inspector Launch sample button missing' }
    Write-Host 'Inspector window and Launch sample control appeared.'

    [BeaconInspectorUiProbe]::Send($launch, 0x00F5, [IntPtr]::Zero, [IntPtr]::Zero) | Out-Null

    $targetWindow = [IntPtr]::Zero
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        Start-Sleep -Milliseconds 250
        $inspector.Refresh()
        if ($inspector.HasExited) { throw "Inspector crashed after launching the target: $($inspector.ExitCode)" }
        $targets = @(Get-Process dotnet -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -eq 'Beacon Counter' })
        if ($targets.Count -ge 1) {
            $target = $targets[0]
            $targetWindow = $target.MainWindowHandle
            if ($targetWindow -ne [IntPtr]::Zero) { break }
        }
    }
    if ($targetWindow -eq [IntPtr]::Zero) { throw 'Inspector failed to launch the Beacon Counter app' }
    Write-Host "Inspector launched target process $($target.Id)"

    $refresh = [BeaconInspectorUiProbe]::FindControl($window, 'Button', 'Refresh')
    if ($refresh -eq [IntPtr]::Zero) { throw 'Inspector Refresh button missing' }
    [BeaconInspectorUiProbe]::Send($refresh, 0x00F5, [IntPtr]::Zero, [IntPtr]::Zero) | Out-Null
    Start-Sleep -Milliseconds 250

    if (-not [BeaconInspectorUiProbe]::HasText($window, 'Static', 'Connected to PID')) {
        throw 'Inspector does not show an attached runtime session'
    }
    if (-not [BeaconInspectorUiProbe]::HasText($window, 'Edit', 'counter: number = 0')) {
        throw 'Inspector did not render live counter = 0'
    }

    $increment = [BeaconInspectorUiProbe]::FindControl($targetWindow, 'Button', 'Increment')
    if ($increment -eq [IntPtr]::Zero) { throw 'Target Increment button missing' }
    [BeaconInspectorUiProbe]::Send($increment, 0x00F5, [IntPtr]::Zero, [IntPtr]::Zero) | Out-Null

    $updated = $false
    for ($attempt = 0; $attempt -lt 10; $attempt++) {
        $refresh = [BeaconInspectorUiProbe]::FindControl($window, 'Button', 'Refresh')
        if ($refresh -eq [IntPtr]::Zero) { throw 'Refresh button disappeared after UI mount' }
        [BeaconInspectorUiProbe]::Send($refresh, 0x00F5, [IntPtr]::Zero, [IntPtr]::Zero) | Out-Null
        Start-Sleep -Milliseconds 200
        if ([BeaconInspectorUiProbe]::HasText($window, 'Edit', 'counter: number = 1')) {
            $updated = $true
            break
        }
    }
    if (-not $updated) { throw 'Inspector UI did not display the updated counter' }
    Write-Host 'Inspector UI observed counter 0 -> 1 from its launched Beacon app.'
}
finally {
    if ($target -ne $null -and -not $target.HasExited) {
        [BeaconInspectorUiProbe]::Post($target.MainWindowHandle, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero) | Out-Null
        if (-not $target.WaitForExit(2500)) { Stop-Process -Id $target.Id -Force -ErrorAction SilentlyContinue }
    }
    if ($inspector -ne $null -and -not $inspector.HasExited) {
        [BeaconInspectorUiProbe]::Post($inspector.MainWindowHandle, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero) | Out-Null
        if (-not $inspector.WaitForExit(2500)) { Stop-Process -Id $inspector.Id -Force -ErrorAction SilentlyContinue }
    }
}
