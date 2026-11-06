# Run the Beacon RPG using the OpenGL extension built from its source.
# Building to the extension directory ensures the host loads the new drawBatch ABI.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    $buildDir = Join-Path $env:TEMP "beacon-rpg-opengl-build"
    dotnet build native/opengl/Beacon.Native.opengl.csproj -c Release -o $buildDir -p:UseAppHost=false
    if ($LASTEXITCODE -ne 0) { throw "Failed to build the native OpenGL extension" }
    Copy-Item (Join-Path $buildDir "Beacon.Native.opengl.dll") native/opengl/Beacon.Native.opengl.dll -Force
    & ./beacon.ps1 examples/rpg-ashen-crypt.beacon
    if ($LASTEXITCODE -ne 0) { throw "The Ashen Crypt exited with code $LASTEXITCODE" }
}
finally {
    Pop-Location
}
