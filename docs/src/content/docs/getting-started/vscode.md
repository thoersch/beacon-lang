---
title: VS Code
description: Install Beacon syntax highlighting and editor behavior in Visual Studio Code.
---

Beacon ships a VS Code extension in the repository. It currently provides **syntax highlighting** and **language configuration** for `.beacon` files.

The extension recognizes Beacon declarations, types, keywords, strings and interpolation, includes, operators, member access, comments, and other language tokens. It also configures `//` comments, bracket pairing, auto-closing pairs, surrounding pairs, and indentation behavior.

## Install the packaged extension

The easiest path is to use the install script from the repository root.

### macOS, Linux, or Git Bash

```bash
./tools/install-vscode.sh
```

### PowerShell

```powershell
./tools/install-vscode.ps1
```

Reload VS Code after installation.

The script reads the current extension version from `editors/vscode/package.json` and installs the packaged `.vsix` with the VS Code CLI.

## Make sure `code` is available

The install scripts use VS Code's `code` command.

Check it with:

```bash
code --version
```

If the command is unavailable, enable the VS Code shell command or install the packaged VSIX manually.

On macOS, open the Command Palette in VS Code and run **Shell Command: Install 'code' command in PATH**.

## Install the VSIX manually

The packaged extension lives in:

```text
editors/vscode/
```

Look for a file named like:

```text
beacon-lang-0.1.1.vsix
```

In VS Code:

1. Open the Extensions view.
2. Open the `...` menu.
3. Choose **Install from VSIX...**.
4. Select the Beacon `.vsix` file.
5. Reload VS Code.

## What you get

Once installed, files ending in `.beacon` are recognized as Beacon source.

```beacon
person: type = {
    name: string
    age: number

    greet: fn() = "Hi, I'm {.name}"
}
```

The extension includes:

- Beacon syntax highlighting
- `.beacon` file association
- `//` line comments
- bracket matching for `{}`, `[]`, and `()`
- automatic closing for brackets and quotes
- surrounding pairs
- indentation rules for types, Lists, Records, conditionals, and loops

## Work on the extension

If you change the grammar or language configuration, rebuild the packaged VSIX.

Node.js 22 or newer is required for extension development.

```bash
cd editors/vscode
npm install
npm run package
```

Then reinstall the generated VSIX:

```bash
code --install-extension beacon-lang-0.1.1.vsix --force
```

Or use the repository install script again after packaging.

## One grammar, editor and docs

Beacon's TextMate grammar lives at:

```text
editors/vscode/syntaxes/beacon.tmLanguage.json
```

The documentation site uses this same grammar for Beacon code blocks, so syntax highlighting in the docs stays aligned with the editor extension.

## Next

Continue with the [syntax tour](../../language/syntax/).
