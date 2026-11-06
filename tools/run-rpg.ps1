# Convenience launcher. beacon.ps1 automatically builds the native OpenGL
# extension when running graphics programs, so no separate build is required.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    & ./beacon.ps1 examples/rpg-ashen-crypt.beacon
    if ($LASTEXITCODE -ne 0) { throw "The Ashen Crypt exited with code $LASTEXITCODE" }
}
finally {
    Pop-Location
}
