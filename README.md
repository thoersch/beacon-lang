# Beacon

**Beacon is a compiled, homoiconic-inspired, and self-hosted programming language, targeting the CLR.**

Beacon combines an explicit, familiar surface syntax with a deliberately small structural foundation. Its compiler is written in Beacon itself, and programs ultimately reduce to three fundamental shapes: Beacon's canonical program representation has only three structural forms:

- **Atom** — a literal or symbol
- **List** — ordered structure
- **Record** — named structure

## What does Beacon look like?

Here's enough Beacon to get a feel for the language:

```beacon
person: type = {
    name: string
    age: number

    greet: fn() = "Hi, I'm {.name}"

    birthday: fn() = [
        .age += 1,
        .age
    ]
}

ada: person = {
    name: "Ada"
    age: 42
}

numbers: list = [1, 2, 3, 4]

double: fn(value: number) = value * 2

print(ada.greet())
print(numbers.map(double))

if ada.age >= 18 then
    print("{ada.name} is an adult")
end
```

Output:

```text
Hi, I'm Ada
[2, 4, 6, 8]
Ada is an adult
```

A few things are visible even in this small example:

- declarations are explicitly typed
- functions are values
- Lists are ordered and use `@` for positional access
- Records and typed values use named fields
- types can define both structure and behavior
- string interpolation is built in
- multi-expression function bodies are Lists
- control flow remains explicit

The full language guide belongs in the Beacon documentation.

## Documentation

The full Beacon documentation is available at **[thoersch.github.io/beacon-lang](https://thoersch.github.io/beacon-lang/)**.

It covers installation, VS Code integration, and a practical tour of Beacon's syntax and language features.

## Getting started

Beacon currently runs directly from a source checkout.

### Requirements

You'll need:

- Git
- .NET 8 or newer (Windows, macOS, or Linux)

Verify .NET:

```bash
dotnet --info
```

### Clone Beacon

```bash
git clone https://github.com/thoersch/beacon-lang.git
cd beacon-lang
```

## Write a program

Create `hello.beacon`:

```beacon
name: string = "world"

greet: fn(value: string) =
    "Hello, {value}!"

print(greet(name))
```

Run it:

```bash
./beacon.sh hello.beacon
```

Output:

```text
Hello, world!
```

The repository's `examples/` directory contains additional runnable programs covering types, Lists, control flow, function clauses, the standard library, and other language features.

## Standard library

Beacon's standard library is written in Beacon too.

Current modules include:

```beacon
include std.text
include std.math
include std.fs
include std.path
```

For example:

```beacon
include std.text
include std.math

name: string = text.trim("  Beacon  ")
root: number = math.sqrt(81)

print(name)
print(root)
```

Beacon keeps native/runtime operations deliberately small. Higher-level functionality belongs in Beacon source when it can be expressed there.

## VS Code support

Beacon includes a VS Code extension with syntax highlighting and editor configuration.

macOS, Linux, or Git Bash:

```bash
./tools/install-vscode.sh
```

PowerShell:

```powershell
./tools/install-vscode.ps1
```

Reload VS Code after installation.

## Self-hosting

Beacon's compiler is written in Beacon.

The canonical compiler begins at:

```text
compiler/compiler.beacon
```

You can verify the compiler's self-hosting fixed point with:

```bash
./beacon.sh self-host
```

## How Beacon reaches the CLR

Beacon compiles directly toward the CLR:

```text
Beacon source
    ↓
Lexer + Parser
    ↓
Atom / List / Record Core
    ↓
Beacon IL planner
    ↓
Symbolic CLR plan
    ↓
Stage-0 CLR assembler/runtime
    ↓
CLR
```

A small frozen Stage-0 binary lives under:

```text
bootstrap/stage0/
```

It solves the bootstrap problem and provides the irreducible boundary to the CLR and operating system.

There is no active C# compiler source in the repository. Beacon's canonical compiler implementation is Beacon.

## Repository layout

```text
compiler/              Beacon compiler source
std/                   standard library
examples/              runnable Beacon programs
bootstrap/stage0/      frozen CLR bootstrap/runtime
editors/vscode/        VS Code support
tools/                 development tooling

beacon.sh
beacon.ps1
beacon.cmd
```

## Project status

Already working:

- self-hosted compiler
- direct CLR execution
- explicit typing and unions
- functions and ordered function clauses
- Lists and Records
- user-defined types
- control flow and loops
- local and standard-library includes
- text, math, filesystem, and path libraries
- VS Code syntax support
- structured compiler diagnostics

Still evolving:

- broader type-system capabilities
- package and dependency management
- standard-library breadth
- executable distribution
- developer tooling
- networking and process APIs
- metaprogramming and reflection

## Explore Beacon

The easiest place to start is:

```bash
./beacon.sh examples/hello.beacon
```

Then browse `examples/`, read the documentation, or take a look at `compiler/compiler.beacon` to see a compiler written in the language it compiles.
