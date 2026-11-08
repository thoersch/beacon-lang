# End-to-end validation of new Beacon OpenGL primitives and timer delivery.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
$process = $null
try {
    $output = Join-Path $env:TEMP "beacon-chess-vector-stdout.txt"
    $errors = Join-Path $env:TEMP "beacon-chess-vector-stderr.txt"
    $process = Start-Process -FilePath "pwsh" -ArgumentList @(
        "-NoProfile", "-File", (Join-Path $root "beacon.ps1"),
        "examples/chess-render-timer-smoke.beacon"
    ) -PassThru -RedirectStandardOutput $output -RedirectStandardError $errors
    if (-not $process.WaitForExit(25000)) {
        throw "Beacon window wake did not arrive within the smoke-test timeout"
    }
    $text = (Get-Content $output -Raw).Trim()
    # The first run can print the native-extension build transcript.
    # The smoke assertions are the three Boolean output lines.
    $checks = @($text -split "[`r`n]+" | Where-Object { $_ -eq "true" -or $_ -eq "false" })
    if ($process.ExitCode -ne 0 -or $checks.Count -ne 3 -or @($checks | Where-Object { $_ -ne "true" }).Count -ne 0) {
        throw "Vector/wake smoke failed, exit $($process.ExitCode). Output: $text Errors: $(Get-Content $errors -Raw)"
    }
    Write-Host "Ellipse/polygon framebuffer pixels and delayed native window event verified."
}
finally {
    if ($null -ne $process -and -not $process.HasExited) { Stop-Process -Id $process.Id -Force }
    Pop-Location
}
