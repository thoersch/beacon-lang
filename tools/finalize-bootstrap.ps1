$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

$Project = Join-Path $Root "Beacon.Compiler/Beacon.Compiler.csproj"
$Program = Join-Path $Root "Beacon.Compiler/Program.cs"
$Compiler = Join-Path $Root "compiler/compiler.beacon"
$Stage0 = Join-Path $Root "bootstrap/stage0"

if (-not (Test-Path $Project) -or -not (Test-Path $Program)) {
    throw "Stage-0 source was not found. This finalizer must be run once from the v0.6 source tree."
}

Write-Host "[1/7] Verifying the source compiler reaches a self-hosting fixed point..."
& dotnet run --project $Project -- $Compiler --self-host
if ($LASTEXITCODE -ne 0) { throw "Self-host verification failed. C# source will not be removed." }

Write-Host "[2/7] Verifying a normal program through the Beacon-written compiler..."
& dotnet run --project $Project -- $Compiler --stage1-run (Join-Path $Root "examples/control-flow.beacon")
if ($LASTEXITCODE -ne 0) { throw "Stage-1 program execution failed. C# source will not be removed." }

$GitCommit = "unknown"
try { $GitCommit = (& git rev-parse HEAD 2>$null).Trim() } catch { }
$ProgramHash = (Get-FileHash $Program -Algorithm SHA256).Hash.ToLowerInvariant()
$ProjectHash = (Get-FileHash $Project -Algorithm SHA256).Hash.ToLowerInvariant()
$Sdk = (& dotnet --version).Trim()

Write-Host "[3/7] Publishing the immutable Stage-0 seed..."
if (Test-Path $Stage0) { Remove-Item $Stage0 -Recurse -Force }
New-Item -ItemType Directory -Path $Stage0 -Force | Out-Null
& dotnet publish $Project -c Release -o $Stage0 -p:UseAppHost=false
if ($LASTEXITCODE -ne 0) { throw "Stage-0 publish failed." }
Get-ChildItem $Stage0 -Filter *.pdb -File -ErrorAction SilentlyContinue | Remove-Item -Force

$Seed = Join-Path $Stage0 "Beacon.Compiler.dll"
if (-not (Test-Path $Seed)) { throw "Published Stage-0 seed was not produced." }

Write-Host "[4/7] Verifying the frozen seed independently..."
& dotnet $Seed $Compiler --self-host
if ($LASTEXITCODE -ne 0) { throw "Frozen Stage-0 seed failed self-host verification. C# source will not be removed." }
& dotnet $Seed $Compiler --stage1-run (Join-Path $Root "examples/control-flow.beacon")
if ($LASTEXITCODE -ne 0) { throw "Frozen Stage-0 seed failed target execution. C# source will not be removed." }

$Timestamp = (Get-Date).ToUniversalTime().ToString("o")
$Provenance = @"
Beacon Stage-0 bootstrap seed
Generated: $Timestamp
Git source commit: $GitCommit
.NET SDK: $Sdk
Beacon.Compiler/Program.cs SHA256: $ProgramHash
Beacon.Compiler/Beacon.Compiler.csproj SHA256: $ProjectHash

The seed was verified by:
  1. compiler.beacon reaching the Stage-1/Stage-2/Stage-3 normalized-plan fixed point
  2. examples/control-flow.beacon compiling and executing through compiler.beacon

The canonical compiler source is compiler/compiler.beacon.
The Stage-0 binary is retained only to bootstrap a clean checkout.
"@
Set-Content -Path (Join-Path $Stage0 "PROVENANCE.txt") -Value $Provenance -Encoding UTF8

$HashLines = @()
Get-ChildItem $Stage0 -File | Where-Object { $_.Name -ne "SHA256SUMS" } | Sort-Object Name | ForEach-Object {
    $Hash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    $HashLines += "$Hash  $($_.Name)"
}
Set-Content -Path (Join-Path $Stage0 "SHA256SUMS") -Value $HashLines -Encoding ASCII

Write-Host "[5/7] Installing final public documentation..."
Copy-Item (Join-Path $Root "tools/final/README.md") (Join-Path $Root "README.md") -Force
Copy-Item (Join-Path $Root "tools/final/BOOTSTRAP.md") (Join-Path $Root "BOOTSTRAP.md") -Force

Write-Host "[6/7] Removing the C# seed source from the active tree..."
Remove-Item (Join-Path $Root "Beacon.Compiler") -Recurse -Force

Write-Host "[7/7] Verifying the final tree contains no C# source..."
$CSharp = Get-ChildItem $Root -Recurse -File | Where-Object {
    $_.FullName -notmatch "[\\/]\.git[\\/]" -and ($_.Extension -eq ".cs" -or $_.Extension -eq ".csproj")
}
if ($CSharp) {
    $Names = ($CSharp | ForEach-Object { $_.FullName }) -join "`n"
    throw "C# source remains in the tree:`n$Names"
}

& dotnet $Seed $Compiler --self-host
if ($LASTEXITCODE -ne 0) { throw "Final tree self-host verification failed." }

Write-Host ""
Write-Host "Beacon source-only transition complete."
Write-Host "Canonical compiler: compiler/compiler.beacon"
Write-Host "Frozen seed:        bootstrap/stage0/Beacon.Compiler.dll"
Write-Host "Run:                .\\beacon.cmd examples\\control-flow.beacon"
Write-Host "Verify:             .\\beacon.cmd self-host"
Write-Host ""
Write-Host "Review 'git status', then commit the bootstrap binary and C# deletions together."
