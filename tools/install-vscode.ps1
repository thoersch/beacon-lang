$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ExtensionDir = Join-Path $Root "editors/vscode"
$PackageJson = Join-Path $ExtensionDir "package.json"

if (-not (Get-Command code -ErrorAction SilentlyContinue)) {
    throw "VS Code's 'code' command was not found in PATH. Enable the shell command in VS Code or install the VSIX manually from editors/vscode/."
}

$Package = Get-Content $PackageJson -Raw | ConvertFrom-Json
$Version = $Package.version

if (-not $Version) {
    throw "Could not read the Beacon VS Code extension version from $PackageJson"
}

$Vsix = Join-Path $ExtensionDir "beacon-lang-$Version.vsix"

if (-not (Test-Path $Vsix)) {
    throw "Packaged Beacon VS Code extension not found: $Vsix. Build it with Node.js 22+: cd editors/vscode; npm install; npm run package"
}

Write-Host "Installing Beacon Language for VS Code ($Version)..."
& code --install-extension $Vsix --force
if ($LASTEXITCODE -ne 0) {
    throw "VS Code extension installation failed with exit code $LASTEXITCODE"
}

Write-Host "Beacon VS Code support installed. Reload VS Code to activate it in open windows."
