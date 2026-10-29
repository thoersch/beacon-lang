# Bootstrapping Beacon

Beacon's canonical compiler is `compiler/compiler.beacon`.

The active repository contains no C# source project. A small immutable CLR seed remains in `bootstrap/stage0/` because every self-hosted compiler needs an initial compiler binary from which to bootstrap.

## Trust boundary

The final architecture is:

```text
bootstrap/stage0/Beacon.Compiler.dll
        |
        | compile compiler/compiler.beacon once
        v
Beacon Stage 1 compiler
        |
        | compile compiler/compiler.beacon
        v
Beacon Stage 2 compiler
        |
        | compile compiler/compiler.beacon
        v
Beacon Stage 3 verification
```

The Stage-0 binary provides only the machine/runtime boundary required to start execution:

- CLR runtime value representation
- native runtime primitives
- `System.Reflection.Emit` access
- conversion of Beacon's symbolic `List<Record>` instruction plan into CLR IL
- process entry and source-file loading

Language policy belongs to Beacon source.

## What the Beacon compiler owns

`compiler/compiler.beacon` contains:

- lexer
- token representation
- recursive-descent parser
- Atom/List/Record Core construction
- explicit type parsing
- rejection of `any`
- arithmetic/comparison/logical lowering
- assignment
- functions and closures
- Lists and Records
- member/index access
- conditionals
- loops
- types and receiver behavior
- symbolic CLR instruction-plan generation

Its main source pipeline is:

```beacon
compileSource: fn(source: string) = [
    tokens: list = lex(source),
    program: list = parseProgram(tokens),
    compile(program)
]
```

## Fixed-point verification

Run:

```bash
./beacon.sh self-host
```

or on Windows:

```bat
beacon.cmd self-host
```

The verification requires the normalized compiler plan to stabilize:

```text
Stage 1 plan == Stage 2 plan
Stage 2 plan == Stage 3 plan
```

This is the project's definition of the compiler reaching its self-hosting fixed point.

## Seed provenance

The frozen seed is accompanied by:

```text
bootstrap/stage0/PROVENANCE.txt
bootstrap/stage0/SHA256SUMS
```

`PROVENANCE.txt` records the source commit, source hashes, SDK version, and the verification performed immediately before the historical C# source was deleted from the active tree.

The repository's git history remains the audit trail for the Stage-0 source.

## Why the seed binary stays

Removing the seed binary would make a clean checkout impossible to bootstrap without obtaining an already-built Beacon compiler from somewhere else.

Keeping one small immutable binary makes the repository self-contained while allowing the compiler implementation itself to remain Beacon source.

This is a standard bootstrapping boundary, not a second canonical compiler implementation.

## Normal compilation

When you run:

```bash
./beacon.sh examples/control-flow.beacon
```

the Stage-0 host first loads the Beacon-written compiler. The target's lexing, parsing, Core construction, and lowering decisions are performed by `compiler.beacon`.

The resulting symbolic plan is then assembled and JIT-executed by the CLR boundary.

## Historical source

The C# seed implementation is intentionally absent from the active source tree after finalization. It remains recoverable through git history and is identified by the provenance metadata stored with the seed binary.

Future compiler behavior belongs in Beacon. Changes to the frozen Stage-0 ABI should be treated as exceptional bootstrap/runtime changes rather than normal language development.
