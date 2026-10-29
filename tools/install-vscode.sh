#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXTENSION_DIR="$ROOT/editors/vscode"
PACKAGE_JSON="$EXTENSION_DIR/package.json"

if ! command -v code >/dev/null 2>&1; then
  echo "VS Code's 'code' command was not found in PATH." >&2
  echo "In VS Code, enable the shell command or install the extension manually from editors/vscode/." >&2
  exit 1
fi

VERSION="$(sed -n 's/^[[:space:]]*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$PACKAGE_JSON" | head -n 1)"

if [[ -z "$VERSION" ]]; then
  echo "Could not read the Beacon VS Code extension version from $PACKAGE_JSON" >&2
  exit 1
fi

VSIX="$EXTENSION_DIR/beacon-lang-$VERSION.vsix"

if [[ ! -f "$VSIX" ]]; then
  echo "Packaged Beacon VS Code extension not found: $VSIX" >&2
  echo "Build it with: cd editors/vscode && nvm use && npm install && npm run package" >&2
  exit 1
fi

echo "Installing Beacon Language for VS Code ($VERSION)..."
code --install-extension "$VSIX" --force

echo "Beacon VS Code support installed. Reload VS Code to activate it in open windows."
