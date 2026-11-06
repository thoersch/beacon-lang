$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$HostAssembly = Join-Path $Root "bootstrap/stage0/Beacon.Compiler.dll"
$Compiler = Join-Path $Root "compiler/compiler.beacon"
$env:BEACON_HOME = $Root

if (-not (Test-Path $HostAssembly)) {
    throw "Beacon bootstrap seed not found: $HostAssembly. Run tools/finalize-bootstrap.ps1 first."
}


# Keep the trusted native OpenGL DLL in sync with the source checkout.
function Ensure-GraphicsExtension([string]$Target) {
    if ($env:OS -ne "Windows_NT" -or -not (Test-Path $Target -PathType Leaf)) { return }
    $source = Get-Content -LiteralPath $Target -Raw
    if ($source -notmatch '(?m)^\s*include\s+std\.graphics(\.gl)?\s*$') { return }
    $dir = Join-Path $Root "native/opengl"
    $project = Join-Path $dir "Beacon.Native.opengl.csproj"
    $sourceHash = (Get-FileHash (Join-Path $dir "Extension.cs") -Algorithm SHA256).Hash
    $projectHash = (Get-FileHash $project -Algorithm SHA256).Hash
    $fingerprint = "$sourceHash-$projectHash"
    $stamp = Join-Path $dir "obj/.beacon-opengl-source-ps1.sha256"
    $installed = Join-Path $dir "Beacon.Native.opengl.dll"
    if (-not (Test-Path $installed) -or -not (Test-Path $stamp) -or (Get-Content $stamp -Raw).Trim() -ne $fingerprint) {
        Write-Host "Beacon: building native OpenGL extension for this checkout..." -ForegroundColor DarkGray
        & dotnet build $project -c Release -p:UseAppHost=false -v:q
        if ($LASTEXITCODE -ne 0) { throw "Could not build the native OpenGL extension" }
        $built = Join-Path $dir "bin/Release/net8.0/Beacon.Native.opengl.dll"
        if (-not (Test-Path $built)) { throw "OpenGL build produced no extension DLL" }
        Copy-Item -LiteralPath $built -Destination $installed -Force
        $stampDir = Split-Path -Parent $stamp
        if (-not (Test-Path $stampDir)) { New-Item -ItemType Directory -Path $stampDir | Out-Null }
        Set-Content -LiteralPath $stamp -Value $fingerprint
    }
}

if ($args.Count -eq 0) {
    Write-Host "Usage:"
    Write-Host "  ./beacon.ps1 file.beacon"
    Write-Host "  ./beacon.ps1 run file.beacon"
    Write-Host "  ./beacon.ps1 plan file.beacon"
    Write-Host "  ./beacon.ps1 inspect file.beacon"
    Write-Host "  ./beacon.ps1 self-host"
    exit 2
}


if ($args[0] -eq "run" -or $args[0] -eq "inspect" -or $args[0] -eq "plan") {
    if ($args.Count -ge 2) { Ensure-GraphicsExtension $args[1] }
} elseif ($args[0] -ne "self-host") {
    Ensure-GraphicsExtension $args[0]
}

switch ($args[0]) {
    "inspect" {
        if ($args.Count -lt 2) { throw "inspect requires a Beacon source file" }
        $Target = (Resolve-Path $args[1]).Path
        & dotnet $HostAssembly $Compiler --stage1-run $Target --inspect
        exit $LASTEXITCODE
    }
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
