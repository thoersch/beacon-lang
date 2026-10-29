$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$SeedProject = Join-Path $Root "tools/seed-refresh/Beacon.Compiler/Beacon.Compiler.csproj"
$SeedOut = Join-Path $Root ".seed-out"
$Stage0 = Join-Path $Root "bootstrap/stage0"
$Compiler = Join-Path $Root "compiler/compiler.beacon"
$Example = Join-Path $Root "examples/includes/main.beacon"

if (-not (Test-Path $SeedProject)) {
    throw "Seed refresh source not found: $SeedProject"
}

Write-Host "Beacon: building refreshed Stage-0 seed..."
Remove-Item $SeedOut -Recurse -Force -ErrorAction SilentlyContinue
& dotnet publish $SeedProject -c Release -o $SeedOut
if ($LASTEXITCODE -ne 0) { throw "Seed build failed" }

New-Item -ItemType Directory -Force -Path $Stage0 | Out-Null
Copy-Item (Join-Path $SeedOut "Beacon.Compiler.dll") $Stage0 -Force
Copy-Item (Join-Path $SeedOut "Beacon.Compiler.deps.json") $Stage0 -Force
Copy-Item (Join-Path $SeedOut "Beacon.Compiler.runtimeconfig.json") $Stage0 -Force

$env:BEACON_HOME = $Root
$HostAssembly = Join-Path $Stage0 "Beacon.Compiler.dll"

Write-Host "Beacon: verifying split compiler self-hosting..."
& dotnet $HostAssembly $Compiler --self-host
if ($LASTEXITCODE -ne 0) { throw "Self-host verification failed" }

Write-Host "Beacon: verifying multi-file include example..."
$output = & dotnet $HostAssembly $Compiler --stage1-run $Example
if ($LASTEXITCODE -ne 0) { throw "Include example failed" }
$output | ForEach-Object { Write-Host $_ }
$text = ($output -join "`n")
if (-not $text.Contains("Hello, I'm Ada")) { throw "Include example did not produce expected greeting" }
if (-not $text.Contains("Boston")) { throw "Include example did not produce expected nested type output" }
if (-not $text.Contains("42")) { throw "Standard-library namespace example did not produce expected math.twice output" }

$dotnetVersion = (& dotnet --version).Trim()
$commit = "unknown"
try { $commit = (& git -C $Root rev-parse HEAD).Trim() } catch { }
$timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

$provenance = @"
Beacon Stage-0 bootstrap seed
=============================

Purpose: immutable CLR bootstrap/runtime boundary for the self-hosted Beacon compiler.
Seed refresh: filesystem/path primitives, seed-only local include composition, and the generic namespace plan operation used by Beacon standard-library namespaces.
Historical implementation language: C#
Source commit before refresh: $commit
.NET SDK: $dotnetVersion
Generated (UTC): $timestamp

The canonical compiler implementation is Beacon source under compiler/.
Stage 1+ resolves includes, lexes, parses, builds Core, and plans CLR IL in Beacon.
"@
Set-Content -Path (Join-Path $Stage0 "PROVENANCE.txt") -Value $provenance -Encoding UTF8

$hashFiles = @("Beacon.Compiler.dll", "Beacon.Compiler.deps.json", "Beacon.Compiler.runtimeconfig.json")
$hashLines = foreach ($name in $hashFiles) {
    $hash = (Get-FileHash (Join-Path $Stage0 $name) -Algorithm SHA256).Hash.ToLowerInvariant()
    "$hash  $name"
}
Set-Content -Path (Join-Path $Stage0 "SHA256SUMS") -Value $hashLines -Encoding ASCII

Write-Host "Beacon: shutting down .NET build servers before cleanup..."
& dotnet build-server shutdown | Out-Null
Start-Sleep -Milliseconds 750

Write-Host "Beacon: removing one-time C# seed refresh source..."
$seedRefresh = Join-Path $Root "tools/seed-refresh"
for ($attempt = 1; $attempt -le 5; $attempt++) {
    try {
        Remove-Item $seedRefresh -Recurse -Force -ErrorAction Stop
        break
    }
    catch {
        if ($attempt -eq 5) { throw }
        Start-Sleep -Milliseconds 750
    }
}
Remove-Item $SeedOut -Recurse -Force -ErrorAction SilentlyContinue

$cs = Get-ChildItem -Path $Root -Recurse -File | Where-Object { $_.Extension -in ".cs", ".csproj" }
if ($cs) {
    $paths = ($cs | ForEach-Object { $_.FullName }) -join "`n"
    throw "C# source remains after seed refresh:`n$paths"
}

Write-Host ""
Write-Host "Beacon include bootstrap complete."
Write-Host "The repository contains no .cs or .csproj files."
Write-Host "Run: ./beacon.sh self-host"
Write-Host "Run: ./beacon.sh examples/includes/main.beacon"
