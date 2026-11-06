<div align="center">

# Beacon

### A compiled, self-hosted programming language for the CLR.

A familiar, explicitly typed syntax. A small structural core. A compiler written in the language it compiles.

[**Documentation**](https://thoersch.github.io/beacon-lang/) · [**Quickstart**](https://thoersch.github.io/beacon-lang/getting-started/installation/) · [**Syntax guide**](https://thoersch.github.io/beacon-lang/language/syntax/) · [**Examples**](examples/) · [**Live Inspector**](https://thoersch.github.io/beacon-lang/tools/inspector/)

[![Compiler](https://github.com/thoersch/beacon-lang/actions/workflows/compiler.yml/badge.svg?branch=master)](https://github.com/thoersch/beacon-lang/actions/workflows/compiler.yml)
[![Documentation](https://github.com/thoersch/beacon-lang/actions/workflows/docs.yml/badge.svg?branch=master)](https://github.com/thoersch/beacon-lang/actions/workflows/docs.yml)
[![Native UI](https://github.com/thoersch/beacon-lang/actions/workflows/window-ui.yml/badge.svg?branch=master)](https://github.com/thoersch/beacon-lang/actions/workflows/window-ui.yml)
[![Live inspection](https://github.com/thoersch/beacon-lang/actions/workflows/live-inspection.yml/badge.svg?branch=master)](https://github.com/thoersch/beacon-lang/actions/workflows/live-inspection.yml)
[![Code style](https://github.com/thoersch/beacon-lang/actions/workflows/style.yml/badge.svg?branch=master)](https://github.com/thoersch/beacon-lang/actions/workflows/style.yml)

</div>

---

Beacon is an experimental language that compiles to the **Common Language Runtime (CLR)**. It provides ordinary language features—functions, types, records, lists, conditionals, modules—and an intentionally minimal compiler representation built from **Atoms, Lists, and Records**.

The canonical compiler is written in Beacon itself. A frozen Stage-0 CLR assembly handles bootstrapping and the current native runtime boundary.

## See the language

```beacon
person: type = {
    name: string
    age: number

    greet: fn() = "Hello, {.name}!"
}

ada: person = {
    name: "Ada"
    age: 42
}

scores: list = [18, 24, 42]
double: fn(value: number) = value * 2

print(ada.greet())
print(scores.map(double))
```

```text
Hello, Ada!
[36, 48, 84]
```

Declarations are explicitly typed; functions can be values; Lists have positional access via `@`, while Records have named members via `.`. Higher-level syntax lowers into the same three structural Core forms.

[Explore the syntax →](https://thoersch.github.io/beacon-lang/language/syntax/)

## Quickstart

**Requirements:** Git and .NET 8 or newer. Beacon currently runs directly from a source checkout; there is no global installer.

```bash
git clone https://github.com/thoersch/beacon-lang.git
cd beacon-lang
./beacon.sh examples/hello.beacon
```

On Windows, use `.\beacon.ps1 examples/hello.beacon` in PowerShell or `beacon.cmd examples\hello.beacon` in Command Prompt.

To compile and execute your own program, save it as `hello.beacon` and run:

```beacon
name: string = "world"

greet: fn(value: string) = "Hello, {value}!"

print(greet(name))
```

```bash
./beacon.sh hello.beacon
```

```text
Hello, world!
```

For shell-specific setup and troubleshooting, see the [installation guide](https://thoersch.github.io/beacon-lang/getting-started/installation/).

## What works today

| Area | Current capability |
| --- | --- |
| **Language** | Explicit types and unions, functions and ordered clauses, user-defined types, Lists and Records, interpolation, conditionals, loops, and modules |
| **Compiler** | Self-hosted Beacon compiler, structured diagnostics, symbolic CLR plans, fixed-point verification |
| **Standard library** | `std.text`, `std.math`, `std.fs`, `std.path`, `std.json` |
| **Desktop** | `std.window` and `std.ui`, with a native Windows backend and structural UI built in Beacon |
| **Inspection** | `std.inspect` for opt-in, read-only snapshots of a running Beacon process |
| **Graphics (experimental)** | `std.graphics` and `std.graphics.gl` with independent native WGL/OpenGL bindings |
| **Editor** | VS Code extension with a Beacon TextMate grammar and language configuration |

**Status:** actively evolving. Desktop windows currently require Windows. Packaging, a broader standard library, and richer debugging remain works in progress.

### Typed collections and inline values

Beacon Lists remain heterogeneous by default, and can opt into pipe-delimited element type constraints such as `list<number>` and `list<item|weapon>`. Named typed Records can be constructed inline with `item { ... }`, while plain Record literals inherit an unambiguous type from their surrounding declaration or List constraint.

[See the RPG inventory example](examples/rpg-typed-inventory.beacon) · [Read the type syntax](https://thoersch.github.io/beacon-lang/language/syntax/#constrained-lists)


## A real application: Beacon Inspector

Beacon Inspector is a native developer tool built in Beacon. It can launch an inspection-enabled application, connect to its process, display source and live variables, and refresh values as the application changes.

On Windows:

```powershell
./beacon.ps1 examples/inspector-ui.beacon
```

Select **Launch sample**, change the counter in the separate Beacon application, then select **Refresh** to see its live state in the Inspector.

[Inspector guide](https://thoersch.github.io/beacon-lang/tools/inspector/) · [Inspector source](examples/inspector-ui.beacon) · [Counter demo](examples/inspector-target.beacon)

## Native graphics without a framework

Beacon's first OpenGL bindings use an independently compiled, package-free module under `native/opengl/`. Application code selects the backend through `graphics.renderer.opengl`, never a magic string, and the frozen bootstrap has no graphics-specific dependency.

On Windows, run the first colored triangle:

```powershell
./beacon.ps1 examples/graphics-triangle.beacon
```

This initial proof targets OpenGL 1.1 compatibility; modern shaders and buffers are planned next.

[Graphics guide](https://thoersch.github.io/beacon-lang/standard-library/graphics/) · [Native extension architecture](https://thoersch.github.io/beacon-lang/concepts/native-extensions/)

## Play a game built in Beacon

**The Ashen Crypt** is a native, turn-based dungeon crawler that expands Beacon's typed RPG inventory example into a full playable game. Explore a tiled crypt, battle pursuing enemies, use potions, level up, and unlock the final gate. The game renders its pixel art and HUD with Beacon-owned OpenGL draw batches.

On Windows, with the .NET 8 SDK:

```powershell
./tools/run-rpg.ps1
```

Use **WASD/arrow keys** to move and attack, **H** to heal, and **R** to restart.

[Game source](examples/rpg-ashen-crypt.beacon) · [Game rules](examples/rpg/rules.beacon) · [Playing guide](docs/src/content/docs/getting-started/rpg-game.md)

## How Beacon works

```text
Beacon source
    ↓
Lexer and parser
    ↓
Atom / List / Record Core
    ↓
Beacon CLR planner
    ↓
Symbolic CLR plan
    ↓
Stage-0 assembler / runtime
    ↓
CLR execution
```

The compiler's implementation is split across `compiler/` and composed by [`compiler/compiler.beacon`](compiler/compiler.beacon). Stage-0 under `bootstrap/stage0/` is the frozen bootstrap boundary, not the language's canonical compiler source.

Verify the self-hosting fixed point:

```bash
./beacon.sh self-host
```

[Read the architecture](https://thoersch.github.io/beacon-lang/concepts/architecture/)

## Explore the project

| Resource | Start here |
| --- | --- |
| **Getting started** | [Installation](https://thoersch.github.io/beacon-lang/getting-started/installation/) and [runnable examples](https://thoersch.github.io/beacon-lang/getting-started/examples/) |
| **Language reference** | [Syntax tour](https://thoersch.github.io/beacon-lang/language/syntax/) |
| **Libraries** | [JSON](https://thoersch.github.io/beacon-lang/standard-library/json/), [window](https://thoersch.github.io/beacon-lang/standard-library/window/), [UI](https://thoersch.github.io/beacon-lang/standard-library/ui/), [inspection](https://thoersch.github.io/beacon-lang/standard-library/inspect/) |
| **Tooling** | [VS Code setup](https://thoersch.github.io/beacon-lang/getting-started/vscode/) and [Inspector](https://thoersch.github.io/beacon-lang/tools/inspector/) |
| **Contributing** | [Contribution guide](CONTRIBUTING.md) and [architecture](https://thoersch.github.io/beacon-lang/concepts/architecture/) |

### Repository layout

```text
compiler/          Self-hosted compiler sources
std/               Beacon standard library
examples/          Runnable Beacon programs and Inspector demos
bootstrap/stage0/  Frozen CLR bootstrap/runtime artifact
editors/vscode/    Beacon grammar and packaged editor extension
docs/              Documentation site (Astro + Starlight)
tools/             Development and validation tooling
```

## Syntax highlighting on GitHub

Beacon code blocks use the `beacon` language identifier. The [documentation site](https://thoersch.github.io/beacon-lang/) and the [VS Code extension](editors/vscode/) share the same syntax grammar and provide full highlighting today.

GitHub's own file highlighting and language-percentage bar require **upstream GitHub Linguist recognition**. A repository-local attribute cannot register a previously unknown language. See [GitHub language recognition](https://thoersch.github.io/beacon-lang/community/language-recognition/) for the current status and contribution path.

---

<div align="center">

**[Read the documentation](https://thoersch.github.io/beacon-lang/) · [Browse the source](compiler/) · [Open an issue](https://github.com/thoersch/beacon-lang/issues)**

</div>
