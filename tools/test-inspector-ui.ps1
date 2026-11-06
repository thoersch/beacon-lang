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

    public static string Describe(IntPtr parent)
    {
        var lines = new List<string>();
        ChildCallback callback = (child, _) =>
        {
            var type = new StringBuilder(128);
            GetClass(child, type, type.Capacity);
            var label = Label(child).Replace("\r", "<CR>").Replace("\n", "<LF>");
            if (label.Length > 240) label = label.Substring(0, 240);
            lines.Add(type.ToString() + ": " + label);
            return true;
        };
        EnumChildWindows(parent, callback, IntPtr.Zero);
        GC.KeepAlive(callback);
        return string.Join("\n", lines);
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

    # The top-level HWND may exist before the Beacon UI finishes mounting
    # its child controls, especially on busy hosted Windows runners.
    $launch = [IntPtr]::Zero
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        $inspector.Refresh()
        if ($inspector.HasExited) { throw "Inspector exited before UI mount: $($inspector.ExitCode)" }
        $window = $inspector.MainWindowHandle
        if ($window -ne [IntPtr]::Zero) {
            $launch = [BeaconInspectorUiProbe]::FindControl($window, 'Button', 'Launch sample')
            if ($launch -ne [IntPtr]::Zero) { break }
        }
        Start-Sleep -Milliseconds 150
    }
    if ($launch -eq [IntPtr]::Zero) {
        Write-Host ([BeaconInspectorUiProbe]::Describe($window))
        throw 'Inspector Launch sample button did not mount'
    }
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

    $attached = $false
    for ($attempt = 0; $attempt -lt 15; $attempt++) {
        # Launch/Refresh remounts all native controls; wait through the
        # short interval when their old HWNDs have been destroyed.
        $refresh = [BeaconInspectorUiProbe]::FindControl($window, 'Button', 'Refresh')
        if ($refresh -eq [IntPtr]::Zero) {
            Start-Sleep -Milliseconds 150
            continue
        }
        [BeaconInspectorUiProbe]::Send($refresh, 0x00F5, [IntPtr]::Zero, [IntPtr]::Zero) | Out-Null
        Start-Sleep -Milliseconds 250
        if ([BeaconInspectorUiProbe]::HasText($window, 'Static', 'Connected to PID') -and
            [BeaconInspectorUiProbe]::HasText($window, 'Edit', 'counter: number = 0')) {
            $attached = $true
            break
        }
    }
    if ($attached) {
        $crlf = [string][char]13 + [char]10
        if (-not [BeaconInspectorUiProbe]::HasText($window, 'Edit', ('include std.window' + $crlf + 'include std.ui'))) {
            throw 'Loaded source did not retain Win32 multiline CRLF separators'
        }
    }
    if (-not $attached) {
        Write-Host 'Inspector control dump:'
        Write-Host ([BeaconInspectorUiProbe]::Describe($window))
        throw 'Inspector did not show its attached counter after repeated Refresh attempts'
    }

    $increment = [BeaconInspectorUiProbe]::FindControl($targetWindow, 'Button', 'Increment')
    if ($increment -eq [IntPtr]::Zero) { throw 'Target Increment button missing' }
    [BeaconInspectorUiProbe]::Send($increment, 0x00F5, [IntPtr]::Zero, [IntPtr]::Zero) | Out-Null

    $updated = $false
    for ($attempt = 0; $attempt -lt 10; $attempt++) {
        # Launch/Refresh remounts all native controls; wait through the
        # short interval when their old HWNDs have been destroyed.
        $refresh = [BeaconInspectorUiProbe]::FindControl($window, 'Button', 'Refresh')
        if ($refresh -eq [IntPtr]::Zero) {
            Start-Sleep -Milliseconds 150
            continue
        }
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
