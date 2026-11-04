---
title: Runnable examples
description: A guided tour of the Beacon examples in the repository.
---

Every program on this page is in the [`examples/` directory](https://github.com/thoersch/beacon-lang/tree/master/examples). Run commands from the repository root after completing [installation](../installation/).

## Start here

```bash
./beacon.sh examples/hello.beacon
```

For more examples, try this progression:

| Program | What it demonstrates |
| --- | --- |
| [`hello.beacon`](https://github.com/thoersch/beacon-lang/blob/master/examples/hello.beacon) | Typed declarations, functions, user-defined types, methods, and interpolation |
| [`control-flow.beacon`](https://github.com/thoersch/beacon-lang/blob/master/examples/control-flow.beacon) | Conditional execution and loops |
| [`conditional-expressions.beacon`](https://github.com/thoersch/beacon-lang/blob/master/examples/conditional-expressions.beacon) | `if / else`, `else if`, and `when / otherwise` expressions |
| [`function-clauses.beacon`](https://github.com/thoersch/beacon-lang/blob/master/examples/function-clauses.beacon) | Ordered function clauses |
| [`list-functional-methods.beacon`](https://github.com/thoersch/beacon-lang/blob/master/examples/list-functional-methods.beacon) | List transformation, filtering, and retrieval |
| [`multiline-expressions.beacon`](https://github.com/thoersch/beacon-lang/blob/master/examples/multiline-expressions.beacon) | Expression continuation across lines |

## Standard-library examples

Each library demonstration runs as an ordinary Beacon program.

```bash
./beacon.sh examples/std-text.beacon
./beacon.sh examples/std-math.beacon
./beacon.sh examples/std-json.beacon
```

Use [`std-fs-path.beacon`](https://github.com/thoersch/beacon-lang/blob/master/examples/std-fs-path.beacon) for filesystem and path operations. Some examples write files; inspect the source before running them in a directory with important data.

The [standard library guides](../../standard-library/json/) cover interfaces and behavior in more detail.

## Native applications and live inspection

Beacon's initial window backend requires Windows.

Run the Inspector from PowerShell:

```powershell
./beacon.ps1 examples/inspector-ui.beacon
```

Select **Launch sample** to start a separate Beacon counter application. Increment the counter in that application, then return to the Inspector and select **Refresh** to read the live value.

To launch a separate application with inspection enabled:

```powershell
./beacon.ps1 inspect examples/inspector-target.beacon
```

See the [Inspector guide](../../tools/inspector/) for the session model, privacy boundaries, and current limitations.

## Verify the compiler

The self-hosted compiler can verify its own fixed point:

```bash
./beacon.sh self-host
```

For a symbolic CLR plan:

```bash
./beacon.sh plan examples/control-flow.beacon
```

This is a useful entry point into the [compiler architecture](../../concepts/architecture/).

## Next steps

Continue with the [syntax tour](../../language/syntax/) or explore [how Beacon compiles](../../concepts/architecture/).
