# Beacon Language for VS Code

VS Code language support for Beacon.

## Install from the Beacon repository

The Beacon repository includes a packaged `.vsix`, so trying the editor support does not require Node.js or npm.

From the Beacon repository root:

### macOS, Linux, or Git Bash

```bash
./tools/install-vscode.sh
```

### PowerShell

```powershell
./tools/install-vscode.ps1
```

The installer uses VS Code's `code --install-extension` command and installs the extension matching the version in this directory's `package.json`.

After installation, reload VS Code. Files ending in `.beacon` are automatically recognized as Beacon.

## Features

- `.beacon` file association
- Syntax highlighting
- `//` comments
- Bracket matching and auto-closing
- Basic indentation support
- Highlighting for:
  - control flow
  - functions and types
  - explicit type annotations and unions
  - local and `std.*` includes
  - strings and interpolation
  - numbers and constants
  - operators
  - member access and implicit receiver syntax

## Building the extension

Building the VSIX requires Node.js 22 or newer.

If you use nvm:

```bash
cd editors/vscode
nvm use 22
npm install
npm run package
```

Without nvm:

```bash
cd editors/vscode
npm install
npm run package
```

`vsce` creates a versioned package such as:

```text
beacon-lang-0.1.0.vsix
```

When the extension version changes, rebuild the VSIX and commit the matching package so a fresh clone remains immediately installable.

## Development

Open the extension directory in VS Code:

```bash
code editors/vscode
```

Then press `F5` to launch an Extension Development Host and open a `.beacon` file.

## Releases

Tags matching `v*` trigger `.github/workflows/vscode-extension.yml`. The workflow packages the extension with Node.js 22 and attaches the generated VSIX to the matching GitHub Release.
