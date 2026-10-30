---
title: Installation
description: Install Beacon from a source checkout and run your first program.
---

Beacon currently runs directly from a source checkout. There is no global installer or package manager yet.

## Requirements

You need:

- **Git**
- **.NET 8 or newer**
- Windows, macOS, or Linux

Verify that .NET is available:

```bash
dotnet --info
```

## Clone Beacon

```bash
git clone https://github.com/thoersch/beacon-lang.git
cd beacon-lang
```

A clean checkout already contains Beacon's frozen Stage-0 runtime, so there is no compiler build step before you can run Beacon.

## Run an included program

### macOS, Linux, or Git Bash

```bash
./beacon.sh examples/hello.beacon
```

### PowerShell

```powershell
./beacon.ps1 examples/hello.beacon
```

### Windows Command Prompt

```bat
beacon.cmd examples\hello.beacon
```

You should see:

```text
3
Hello, Beacon! I'm Ada
37
```

## Write your first program

Create a file named `hello.beacon` in the repository root:

```beacon title="hello.beacon"
name: string = "world"

greet: fn(value: string) =
    "Hello, {value}!"

print(greet(name))
```

Run it with the launcher for your shell:

```bash
./beacon.sh hello.beacon
```

Output:

```text
Hello, world!
```

## The launchers

Beacon includes three equivalent launchers at the repository root:

| Environment | Launcher |
| --- | --- |
| macOS / Linux / Git Bash | `./beacon.sh` |
| PowerShell | `./beacon.ps1` |
| Windows Command Prompt | `beacon.cmd` |

Pass a `.beacon` file to execute it:

```bash
./beacon.sh path/to/program.beacon
```

You can also ask Beacon to verify its self-hosting fixed point:

```bash
./beacon.sh self-host
```

Or inspect the symbolic compiler plan produced for a program:

```bash
./beacon.sh plan examples/control-flow.beacon
```

## Troubleshooting

### `dotnet` is not found

Install a current .NET runtime or SDK and restart your terminal so the `dotnet` command is available on `PATH`.

### `beacon.sh` is not executable

On Unix-like systems, restore the executable bit if your checkout lost it:

```bash
chmod +x beacon.sh
```

### PowerShell blocks local scripts

If your system policy blocks `beacon.ps1`, you can use `beacon.cmd` from Command Prompt or review your PowerShell execution policy before changing it.

## Next

Install the [VS Code integration](../vscode/) or continue to the [syntax tour](../../language/syntax/).
