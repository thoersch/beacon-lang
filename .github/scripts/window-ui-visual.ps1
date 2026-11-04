$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$env:BEACON_HOME = $root

Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

public static class BeaconVisualProbe
{
    public delegate bool ChildCallback(IntPtr child, IntPtr param);

    [DllImport("user32.dll", CharSet = CharSet.Unicode, EntryPoint = "FindWindowW")]
    public static extern IntPtr FindWindow(string className, string title);

    [DllImport("user32.dll", CharSet = CharSet.Unicode, EntryPoint = "GetClassNameW")]
    public static extern int GetClassName(IntPtr hwnd, StringBuilder result, int maximum);

    [DllImport("user32.dll", CharSet = CharSet.Unicode, EntryPoint = "SendMessageW")]
    public static extern IntPtr SendTextMessage(IntPtr hwnd, uint message, IntPtr capacity, StringBuilder result);

    [DllImport("user32.dll")]
    public static extern bool EnumChildWindows(IntPtr parent, ChildCallback callback, IntPtr param);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hwnd);

    [DllImport("user32.dll")]
    public static extern bool UpdateWindow(IntPtr hwnd);

    [DllImport("user32.dll")]
    public static extern bool PostMessageW(IntPtr hwnd, uint message, IntPtr wParam, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern IntPtr GetDC(IntPtr hwnd);

    [DllImport("user32.dll")]
    public static extern int ReleaseDC(IntPtr hwnd, IntPtr dc);

    [DllImport("gdi32.dll")]
    public static extern uint GetPixel(IntPtr dc, int x, int y);

    [DllImport("user32.dll")]
    public static extern bool PrintWindow(IntPtr hwnd, IntPtr dc, uint flags);

    public static IntPtr[] Children(IntPtr parent)
    {
        var list = new List<IntPtr>();
        ChildCallback callback = (child, param) => { list.Add(child); return true; };
        EnumChildWindows(parent, callback, IntPtr.Zero);
        GC.KeepAlive(callback);
        return list.ToArray();
    }

    public static string Class(IntPtr hwnd)
    {
        var value = new StringBuilder(128);
        GetClassName(hwnd, value, value.Capacity);
        return value.ToString();
    }

    public static string Text(IntPtr hwnd)
    {
        var value = new StringBuilder(8192);
        SendTextMessage(hwnd, 0x000D, (IntPtr)value.Capacity, value);
        return value.ToString();
    }

    public static uint Pixel(IntPtr hwnd, int x, int y)
    {
        var dc = GetDC(hwnd);
        if (dc == IntPtr.Zero) throw new Exception("GetDC failed for Inspector");
        try { return GetPixel(dc, x, y); }
        finally { ReleaseDC(hwnd, dc); }
    }

}
'@

$stdout = Join-Path $env:RUNNER_TEMP 'beacon-inspector-stdout.txt'
$stderr = Join-Path $env:RUNNER_TEMP 'beacon-inspector-stderr.txt'
$compiler = Join-Path $root 'bootstrap/stage0/Beacon.Compiler.dll'
$sourceCompiler = Join-Path $root 'compiler/compiler.beacon'
$inspector = Join-Path $root 'examples/inspector-ui.beacon'

$process = Start-Process -FilePath 'dotnet' -ArgumentList @(
    $compiler, $sourceCompiler, '--stage1-run', $inspector
) -WorkingDirectory $root -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru

$window = [IntPtr]::Zero
try {
    for ($attempt = 0; $attempt -lt 100; $attempt++) {
        $process.Refresh()
        $window = $process.MainWindowHandle
        if ($window -ne [IntPtr]::Zero -and [BeaconVisualProbe]::IsWindowVisible($window)) { break }
        Start-Sleep -Milliseconds 200
        if ($process.HasExited) {
            throw "Inspector terminated early (exit $($process.ExitCode)): $(Get-Content $stderr -Raw)"
        }
    }
    if ($window -eq [IntPtr]::Zero) {
        Write-Host "Inspector PID $($process.Id), HasExited=$($process.HasExited)"
        Get-Process -Id $process.Id -ErrorAction SilentlyContinue | Format-List Id,ProcessName,MainWindowHandle,MainWindowTitle,SessionId
        if (Test-Path $stdout) { Write-Host "stdout:"; Get-Content $stdout }
        if (Test-Path $stderr) { Write-Host "stderr:"; Get-Content $stderr }
        Get-Process -Name dotnet -ErrorAction SilentlyContinue | Select-Object Id,MainWindowTitle,MainWindowHandle,SessionId | Format-Table
        throw 'Inspector window never appeared'
    }
    if (-not [BeaconVisualProbe]::IsWindowVisible($window)) { throw 'Inspector window is not visible' }
    [BeaconVisualProbe]::UpdateWindow($window) | Out-Null
    Start-Sleep -Milliseconds 300

    $children = @([BeaconVisualProbe]::Children($window))
    $statics = @($children | Where-Object { [BeaconVisualProbe]::Class($_) -eq 'Static' })
    $edits = @($children | Where-Object { [BeaconVisualProbe]::Class($_) -eq 'Edit' })
    $buttons = @($children | Where-Object { [BeaconVisualProbe]::Class($_) -eq 'Button' })

    # Before the fix, each panel was an empty full-width STATIC window covering its children.
    $staticLabels = @($statics | ForEach-Object { [BeaconVisualProbe]::Text($_) })
    if ($staticLabels -contains '') {
        throw "Empty STATIC child window (covering-panel regression): $($staticLabels -join ', ')"
    }
    foreach ($expected in @('Beacon Inspector', 'Source', 'Live variables')) {
        if ($staticLabels -notcontains $expected) {
            throw "Missing visible label '$expected'; found $($staticLabels -join ', ')"
        }
    }
    if ($edits.Count -ne 3) { throw "Expected search plus two code EDIT controls, got $($edits.Count)" }
    if ($buttons.Count -ne 4) { throw "Expected Launch, Refresh, Expand and Attach buttons, got $($buttons.Count)" }

    $editTexts = @($edits | ForEach-Object { [BeaconVisualProbe]::Text($_) })
    $sourceText = @($editTexts | Where-Object { $_ -like 'Launch the sample application*' })
    if ($sourceText.Count -ne 1) { throw "Disconnected source panel not found: $($editTexts -join ' | ')" }
    if ($editTexts -notcontains 'No variables available. Connect to a running Beacon application.') {
        throw 'Inspector missing the disconnected live-variable message'
    }

    # Compare real pixels from the parent and first panel's unobstructed edge.
    $background = [BeaconVisualProbe]::Pixel($window, 4, 4)
    $panel = [BeaconVisualProbe]::Pixel($window, 35, 200)
    $expectedBackground = [uint32](12 -bor (16 -shl 8) -bor (22 -shl 16))
    $expectedPanel = [uint32](21 -bor (27 -shl 8) -bor (36 -shl 16))
    if ($background -ne $expectedBackground) {
        throw ("Incorrect background pixel: 0x{0:X6} expected 0x{1:X6}" -f $background, $expectedBackground)
    }
    if ($panel -ne $expectedPanel) {
        throw ("Incorrect panel pixel: 0x{0:X6} expected 0x{1:X6}" -f $panel, $expectedPanel)
    }

    # The dark Win32 theme previously rendered an entirely invisible cue banner.
    # Read pixels from the native input HWND so the test fails on a blank field.
    $searchHandle = @($edits | Where-Object { [BeaconVisualProbe]::Text($_) -eq '' })
    if ($searchHandle.Count -ne 1) { throw 'Could not identify the empty search input' }
    $hintPixels = 0
    for ($x = 10; $x -lt 135; $x += 2) {
        for ($y = 4; $y -lt 25; $y += 2) {
            $pixel = [BeaconVisualProbe]::Pixel($searchHandle[0], $x, $y)
            $red = [int]($pixel -band 255)
            $green = [int](($pixel -shr 8) -band 255)
            $blue = [int](($pixel -shr 16) -band 255)
            if ($red -ge 100 -and $red -le 190 -and
                $green -ge 110 -and $green -le 205 -and
                $blue -ge 130 -and $blue -le 230) {
                $hintPixels += 1
            }
        }
    }
    if ($hintPixels -lt 5) { throw "Native search placeholder is invisible ($hintPixels text-colored pixels)" }

    $captureDir = Join-Path $root '.native-tests'
    New-Item -ItemType Directory -Force -Path $captureDir | Out-Null
    $capture = Join-Path $captureDir 'beacon-inspector-visual.png'
    try {
        Add-Type -AssemblyName System.Drawing
        $bitmap = [System.Drawing.Bitmap]::new(1220, 800)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        try {
            $dc = $graphics.GetHdc()
            try { $captured = [BeaconVisualProbe]::PrintWindow($window, $dc, 2) }
            finally { $graphics.ReleaseHdc($dc) }
            if ($captured) {
                $bitmap.Save($capture, [System.Drawing.Imaging.ImageFormat]::Png)
                Write-Host "Captured $capture"
            } else {
                Write-Warning 'PrintWindow unsupported on this runner; pixel assertions passed'
            }
        }
        finally { $graphics.Dispose(); $bitmap.Dispose() }
    }
    catch {
        Write-Warning "Native screenshot unavailable: $_"
    }
    Write-Host "Inspector visuals passed: $($statics.Count) labels, $($buttons.Count) buttons, $($edits.Count) edits, parent/panel pixels, $hintPixels placeholder pixels."
}
finally {
    if ($window -ne [IntPtr]::Zero) {
        [BeaconVisualProbe]::PostMessageW($window, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero) | Out-Null
    }
    if (-not $process.HasExited) {
        try { $process.WaitForExit(4000) | Out-Null } catch {}
    }
    if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue }
}
