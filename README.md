# Beacon Lang

Beacon is a compiled, homoiconic-inspired self-hosting programming language targeting the CLR.

Its compiler is written in Beacon, and its canonical program representation has only three structural shapes:

- **Atom** — a literal or symbol
- **List** — ordered structure
- **Record** — named structure

Beacon keeps a small frozen Stage-0 CLR seed in `bootstrap/stage0/` so a clean checkout can compile `compiler/compiler.beacon`. There is **no C# source in the project**.

## Quick start

Requirements:

- .NET 8 runtime or newer compatible runtime

Verify .NET:

```bash
dotnet --info
```

Run a Beacon program on Windows:

```bat
beacon.cmd examples\control-flow.beacon
```

PowerShell:

```powershell
./beacon.ps1 examples/control-flow.beacon
```

macOS / Linux / Git Bash:

```bash
./beacon.sh examples/control-flow.beacon
```

Expected output:

```text
42 is old!
Age check passed
I'm younger than 55
I'm younger than 49
42
```

## VS Code support

Beacon ships with a packaged VS Code extension for `.beacon` syntax highlighting and editor behavior. A fresh clone can install it without Node.js or npm.

macOS, Linux, or Git Bash:

```bash
./tools/install-vscode.sh
```

PowerShell:

```powershell
./tools/install-vscode.ps1
```

Reload VS Code after installation. The packaged extension lives in `editors/vscode/` and is rebuilt with Node.js 22+ when the extension source changes.

For extension development:

```bash
cd editors/vscode
nvm use 22
npm install
npm run package
```

## Verify self-hosting

Beacon can compile its own compiler to a fixed point:

```bat
beacon.cmd self-host
```

or:

```bash
./beacon.sh self-host
```

A successful run verifies:

```text
Stage 0 seed -> compiler.beacon
compiler.beacon -> Stage 1 plan
Stage 1 compiler -> Stage 2 plan
Stage 2 compiler -> Stage 3 verification plan
```

The normalized Stage 1, Stage 2, and Stage 3 compiler plans must reproduce one another.

## Language example

```beacon
person: type = {
    name: string
    age: number

    greet: fn(greeting: string) =
        "{greeting}, I'm {.name}"

    birthday: fn() = [
        .age += 1,
        .age
    ]
}

ada: person = {
    name: "Ada"
    age: 42
}

ages: list = [24, 55, 9, 17, 49]

if ada.age > 40 then
    print(ada.age, "is old!")
else
    print("Young!")
end

for [i: number = 0, i < ages.length(), i += 1]
    if ada.age < ages@i then
        print("Ada is younger than", ages@i)
    end
loop
```

## Multiline expressions

A newline may follow an operator when the expression clearly continues. This keeps long expressions readable without introducing a continuation token:

```beacon
endsWith: fn(str: string, search: string) =
    search.length() <= str.length() and
    str.slice(str.length() - search.length(), search.length()) == search

result: number =
    1 +
    2 *
    3
```

The operator stays on the preceding line. A newline before an operator still ends the expression, preserving Beacon's statement boundaries.

## Typing

Beacon requires explicit types. There is no `any` type.

```beacon
age: number = 42
name: string = "Ada"
values: list = [1, 2, 3]
```

Compiler code uses explicit unions when a value can have more than one structural shape:

```beacon
emit: fn(node: atom | list | record) = ...
```

## Lists and Records

Lists are ordered and require commas:

```beacon
values: list = [1, 2, 3]
```

Records are named structures:

```beacon
person: record = {
    name: "Ada"
    age: 42
}
```

List indexing uses `@`:

```beacon
values@0
values@i
values@(i + 1)
```

Lists use stack-style mutation methods:

```beacon
values.push(42)   // append to the end
last = values.pop() // remove and return the final value
```

`pop()` fails on an empty List. The previous `append()` name is not retained as an alias.

Member access uses `.`:

```beacon
person.name
```

`@` is exclusively positional List access. Records are named structures and Strings are not Lists, so neither supports `@`. When a Record key is data rather than a statically known name, use the explicit Record methods:

```beacon
field: string = "name"
print(person.get(field))
person.set(field, "Grace")
```

Inside type behavior, a leading `.` refers to the current receiver:

```beacon
birthday: fn() = [
    .age += 1,
    .age
]
```

## Functions

Single-expression function:

```beacon
square: fn(x: number) = x * x
```

Multiple expressions use a List; the final expression is the result:

```beacon
incrementTwice: fn(x: number) = [
    x += 1,
    x += 1,
    x
]
```

A function may also be defined as an ordered List of matching clauses:

```beacon
format: fn = [
    fn(value: string) = "text: {value}",
    fn(value: number) = "number: {value}"
]
```

Function clauses are pattern matching, not ranked overload resolution. Beacon tries clauses from top to bottom and executes the first clause whose arity and parameter types match the arguments. Union and named types participate in the same type matching rules. Return types never participate in dispatch.

Because clause order is semantic, broader patterns can deliberately precede narrower ones:

```beacon
classify: fn = [
    fn(value: atom) = "atom",
    fn(value: string) = "string"
]

print(classify("Beacon")) // atom
```

The declaration remains one binding named `format`; the clause List is part of the function's program structure rather than a set of repeated declarations.

## Conditionals

```beacon
if age >= 18 then
    print("adult")
else
    print("minor")
end
```

## Iteration

```beacon
for [i: number = 0, i < values.length(), i += 1]
    print(values@i)
loop
```

## Operators

Arithmetic:

```text
+  -  *  /
```

Comparison:

```text
==  !=  <  <=  >  >=
```

Logical:

```text
and  or  not
```

Unary negation:

```beacon
x: number = -1
y: number = -x
z: number = -(x + 5)
```

Loop control uses `break` and `continue`. Both target the innermost loop; `continue` executes the `for` step before re-checking its condition:

```beacon
for [i: number = 0, i < values.length(), i += 1]
    if values@i == 0 then
        continue
    end

    if values@i < 0 then
        break
    end

    print(values@i)
loop
```

Using `break` or `continue` outside a loop is a compile error. Function bodies are separate control-flow scopes, so a function declared inside a loop cannot break or continue that enclosing loop.

Assignment:

```text
=  +=
```

## Compiler architecture

The canonical compiler lives at:

```text
compiler/compiler.beacon
```

It owns:

- tokenization
- parsing
- Atom/List/Record Core construction
- explicit type annotation parsing
- control-flow lowering
- function/type lowering
- symbolic CLR instruction planning

The pipeline is:

```text
Beacon source
    -> Beacon lexer
    -> Beacon parser
    -> Atom / List / Record Core
    -> Beacon IL planner
    -> List<Record> CLR plan
    -> frozen Stage-0 CLR assembler/runtime
    -> CLR CIL
    -> JIT execution
```

The Stage-0 seed does not decide what Beacon syntax means. It is the trusted machine boundary that turns the already-decided symbolic instruction plan into CLR instructions and provides the small runtime ABI.

## Inspect a compiler plan

Windows:

```bat
beacon.cmd plan examples\control-flow.beacon
```

Unix / Git Bash:

```bash
./beacon.sh plan examples/control-flow.beacon
```

## Repository layout

```text
bootstrap/
    stage0/                 frozen CLR seed + provenance/hashes

compiler/
    compiler.beacon         canonical Beacon compiler source

examples/
    *.beacon

beacon.cmd                  Windows launcher
beacon.ps1                  PowerShell launcher
beacon.sh                   macOS/Linux/Git Bash launcher

README.md
```

There is no active C# source project.

## Why is there a binary seed?

A self-hosted compiler has a bootstrap problem: source code cannot compile itself before a compiler already exists.

Beacon therefore keeps one immutable Stage-0 CLR binary. That binary was produced by the final historical C# seed compiler and verified against the self-hosted compiler before the C# source was removed from the active tree.

Its provenance and SHA-256 hashes are stored beside it in:

```text
bootstrap/stage0/PROVENANCE.txt
bootstrap/stage0/SHA256SUMS
```

The canonical compiler implementation is Beacon source. The binary seed exists only to start from a clean checkout.

## Project status

Beacon is experimental and pre-alpha.

Current focus:

- small semantic core
- explicit typing
- self-hosting
- direct CLR targeting
- code/data structural duality
- moving standard-library functionality into Beacon

Future work includes modules, file/network capabilities, persistent executable output, richer type checking, package tooling, and editor support.
