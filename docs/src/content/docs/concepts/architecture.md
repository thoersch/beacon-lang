---
title: Compiler architecture
description: How Beacon source becomes CLR execution, and what self-hosting means.
---

Beacon is a compiled language targeting the Common Language Runtime. Its canonical compiler is written in Beacon and lives under [`compiler/`](https://github.com/thoersch/beacon-lang/tree/master/compiler). The repository retains a frozen CLR bootstrap/runtime assembly.

## The compilation pipeline

```text
Source (.beacon)
      │
      ▼
Lexer and parser
      │
      ▼
Atom / List / Record Core
      │
      ▼
Beacon emitter / CLR planner
      │
      ▼
Symbolic CLR plan
      │
      ▼
Stage-0 CLR assembler and runtime
      │
      ▼
CLR execution
```

| Stage | Implementation |
| --- | --- |
| Tokenization and parsing | `compiler/lexer.beacon`, `compiler/parser.beacon` |
| Core composition and includes | `compiler/core.beacon`, `compiler/source-map.beacon` |
| Type checking and diagnostics | `compiler/typecheck.beacon`, `compiler/diagnostics.beacon` |
| Symbolic CLR emission | `compiler/emitter.beacon` |
| Compiler entry point | `compiler/compiler.beacon` |
| Bootstrap assembly/runtime | `bootstrap/stage0/` |

## Three Core forms

The canonical program representation uses three structural shapes:

- **Atom** — a literal or symbol
- **List** — an ordered sequence or structural form
- **Record** — a named collection of values

Ordinary conditional syntax lowers into existing structural forms, avoiding a new fundamental Core object. This keeps the compiler model small while the surface language can evolve independently.

The same principle applies outside the compiler: UI elements in `std.ui` are Records and Lists, and structured diagnostics are ordinary Beacon data.

## Self-hosting and Stage-0

Stage-0 solves the bootstrap problem. A compiled seed exists so the compiler written in Beacon can compile itself from a clean checkout.

```bash
./beacon.sh self-host
```

This checks the self-hosting fixed point by comparing normalized compiler plans. It runs in CI and is a useful prerequisite before merging compiler changes.

Stage-0 currently also contains runtime services used by compiled apps, including native desktop and inspection boundaries. This is an architectural constraint, not a reason to move higher-level behavior into the host. Standard-library logic belongs in Beacon when possible; the host should expose only irreducible platform operations.

Separating the evolving runtime from the bootstrap seed is a future architectural step.

## Inspect a generated plan

```bash
./beacon.sh plan examples/control-flow.beacon
```

The emitter describes CLR operations symbolically. The frozen assembler realizes that plan for execution.

## Includes and modularity

Quoted includes compose local files into the current namespace:

```beacon
include "models/address"
```

Dotted standard-library includes load an isolated namespace:

```beacon
include std.json

value: record = json.parse("{\"enabled\":true}")
```

Functions are public by default. A named module-level function may opt into `fn<private>(...)` to stay internal to that module.

## Source maps and diagnostics

The compiler tracks source file/line/column information beside Core rather than embedding source positions as additional fundamental Core forms. Structured diagnostics retain severity, phase, path, and hints and can be rendered for terminal users.

## Contributing to the compiler

Follow the [contribution guide](https://github.com/thoersch/beacon-lang/blob/master/CONTRIBUTING.md). Keep self-hosting green, avoid adding new Core kinds for structurally expressible constructs, and verify portable behavior when touching host boundaries.
