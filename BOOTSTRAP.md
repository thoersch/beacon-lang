# Bootstrapping Beacon

Beacon's long-term compiler is intended to be written in Beacon.

The bootstrap is deliberately staged so the existing compiler remains a stable recovery path while compiler responsibilities move into the language itself.

## Stages

### Stage 0 — C# bootstrap compiler

`Beacon.Compiler` is the current Stage-0 compiler. It owns:

- lexing and parsing Beacon source
- lowering source into Atom / List / Record Core
- direct CLR IL emission with `System.Reflection.Emit`
- the small CLR runtime used by compiled Beacon code

Stage 0 should remain buildable even after Beacon becomes self-hosting. It is the trusted seed compiler.

### Stage 1 — Beacon consumes Beacon Core

v0.4 introduced the first executable self-hosting boundary.

`compiler/compiler.beacon` is compiled by Stage 0, executed as a Beacon program, and then receives the Stage-0 canonical Core of another Beacon source file.

Run it with:

```bash
dotnet run --project ./Beacon.Compiler/Beacon.Compiler.csproj -- ./compiler/compiler.beacon --stage1 ./examples/stage1-target.beacon
```

The flow is:

```text
compiler/compiler.beacon
        |
        | compiled by Stage 0
        v
Beacon compiler functions
        ^
        |
target.beacon -> Stage-0 lexer/parser -> Atom/List/Record runtime value
        |
        v
symbolic CLR IL plan produced by Beacon
```

The important milestone is that compiler logic can execute in Beacon over Beacon's own canonical program representation.

### Stage 1.5 — Beacon plan, host assembler

v0.5 makes that boundary executable. `compiler/compiler.beacon` lowers the target Core into a symbolic instruction plan and `PlanAssembler` translates only that already-decided plan into `System.Reflection.Emit` calls.

Inspect the plan:

```bash
dotnet run --project ./Beacon.Compiler/Beacon.Compiler.csproj -- ./compiler/compiler.beacon --stage1 ./examples/stage1-target.beacon
```

Compile the target through Beacon's compiler logic and run it:

```bash
dotnet run --project ./Beacon.Compiler/Beacon.Compiler.csproj -- ./compiler/compiler.beacon --stage1-run ./examples/stage1-target.beacon
```

The included target prints `3` and `true`. C# still lexes/parses the target and the Stage-1 plan currently supports only a subset of Core forms, but target lowering policy is now on the Beacon side of the boundary.

### Stage 2 — Complete IL planning in Beacon

Continue expanding `compiler/compiler.beacon` until it can lower every Core form emitted by the parser:

- definitions
- function creation and calls
- Records and Lists
- member access
- assignment
- branching
- loops
- comparisons
- types

The output remains ordinary Beacon data: a `List<Record>` describing CLR operations and operands.

### Stage 3 — Tiny host IL assembler

Keep only a small CLR-facing assembler in C#:

```text
List<Record> IL plan
        |
        v
System.Reflection.Emit
        |
        v
CLR CIL
```

At this point the host no longer contains language compilation policy. It only translates an already-decided IL plan into CLR instructions.

### Stage 4 — Lexer and parser in Beacon

Once the compiler backend is stable, move the reader into Beacon:

```text
String source
    -> Beacon lexer
    -> List<Record> tokens
    -> Beacon parser
    -> Atom / List / Record Core
    -> Beacon compiler
    -> IL plan
```

The Stage-0 parser remains available only for bootstrapping and validation.

### Stage 5 — Fixed-point bootstrap

When the Beacon compiler can compile its own source:

```text
Stage 0 compiles compiler.beacon -> Stage 1 compiler
Stage 1 compiles compiler.beacon -> Stage 2 compiler
Stage 2 compiles compiler.beacon -> Stage 3 compiler
```

The normalized compiler output from Stage 2 and Stage 3 should match. That fixed point is the self-hosting milestone.

## Why expose Core as normal Beacon values?

The Stage-0 bridge maps compiler Core directly into Beacon's runtime vocabulary:

- Symbol Atom -> Beacon `symbol`
- Number Atom -> `number`
- String Atom -> `string`
- Boolean Atom -> `boolean`
- Null Atom -> `null`
- List Core -> `list`
- Record Core -> Record

A Symbol is still an Atom, but remains distinguishable from a string literal. Its text is available through `.name`.

That means compiler code does not need a private AST object model. It works with the same structural vocabulary as ordinary Beacon programs.

## Bootstrap-oriented runtime primitives

v0.4 adds the small set of operations needed to begin writing compiler code naturally:

```beacon
kind(value)
fail(message)

list.length()
list.append(value)
list.concat(other)

string.length()
string.slice(start)
string.slice(start, length)
string.startsWith(prefix)

record.keys()
record.has(key)

value@index
value@index = replacement

and
or
not
```

`@` now means keyed/indexed access rather than List-only access:

```beacon
items@0
source@3
record@"name"
```

This keeps the language surface small while giving compiler code the data-manipulation tools it needs.


## Typing during bootstrap

Beacon deliberately has no `any` type. Compiler code uses explicit structural unions when it genuinely accepts multiple canonical shapes:

```beacon
emit: fn(node: atom | list | record) = ...
```

This keeps the self-hosted compiler honest about the values flowing through it instead of relying on an untyped escape hatch.
