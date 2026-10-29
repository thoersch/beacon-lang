$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$HostAssembly = Join-Path $Root "bootstrap/stage0/Beacon.Compiler.dll"
$Compiler = Join-Path $Root "compiler/compiler.beacon"
$env:BEACON_HOME = $Root

if (-not (Test-Path $HostAssembly)) {
    throw "Beacon bootstrap seed not found: $HostAssembly. Run tools/finalize-bootstrap.ps1 first."
}

if ($args.Count -eq 0) {
    Write-Host "Usage:"
    Write-Host "  ./beacon.ps1 file.beacon"
    Write-Host "  ./beacon.ps1 run file.beacon"
    Write-Host "  ./beacon.ps1 plan file.beacon"
    Write-Host "  ./beacon.ps1 self-host"
    exit 2
}

switch ($args[0]) {
    "self-host" {
        & dotnet $HostAssembly $Compiler --self-host
        exit $LASTEXITCODE
    }
    "plan" {
        if ($args.Count -lt 2) { throw "plan requires a Beacon source file" }
        $Target = (Resolve-Path $args[1]).Path
        & dotnet $HostAssembly $Compiler --stage1 $Target
        exit $LASTEXITCODE
    }
    "run" {
        if ($args.Count -lt 2) { throw "run requires a Beacon source file" }
        $Target = (Resolve-Path $args[1]).Path
        & dotnet $HostAssembly $Compiler --stage1-run $Target
        exit $LASTEXITCODE
    }
    default {
        $Target = (Resolve-Path $args[0]).Path
        & dotnet $HostAssembly $Compiler --stage1-run $Target
        exit $LASTEXITCODE
    }
}
