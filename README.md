# Beacon Lang

**Beacon** is an experimental programming language built around one small idea:

> Programs and data should share the same structural vocabulary.

Beacon has three canonical shapes:

- **Atom** — a single value or symbol
- **List** — ordered structure
- **Record** — named structure

The surface syntax is designed to remain explicit and readable as programs grow, while the compiler lowers Beacon source into Atom/List/Record structures and compiles them directly to **CLR Common Intermediate Language (CIL)**.

Beacon is currently a pre-alpha language prototype. The bootstrap compiler is written in C# and targets .NET 8.

## A first Beacon program

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

print(ada.greet("Hello"))
print(ada.birthday())
```

Beacon intentionally uses different delimiters for different kinds of structure:

```text
[...]   ordered structure
{...}   named structure
.       member access
@       list indexing
```

Lists require commas. Records may use newlines between fields.

---

## Requirements

Beacon currently requires the **.NET 8 SDK** on Windows, macOS, or Linux.

Verify your SDK installation:

```bash
dotnet --version
```

You should see an 8.x SDK or a newer compatible SDK.

Download .NET from:

https://dotnet.microsoft.com/download/dotnet/8.0

---

## Build Beacon

Open a terminal in the repository root. The directory should contain:

```text
Beacon.Compiler/
examples/
README.md
```

Build the compiler:

```bash
dotnet build ./Beacon.Compiler/Beacon.Compiler.csproj
```

---

## Run a Beacon program

Run the included control-flow example:

```bash
dotnet run --project ./Beacon.Compiler/Beacon.Compiler.csproj -- ./examples/control-flow.beacon --run
```

Run your own Beacon source file:

```bash
dotnet run --project ./Beacon.Compiler/Beacon.Compiler.csproj -- ./path/to/program.beacon --run
```

Beacon currently compiles programs to in-memory CLR IL and executes that IL through the .NET JIT.

It does **not yet** write standalone `.dll` or `.exe` files.

### Try the Stage-1 bootstrap

Beacon can now use compiler logic written in Beacon to lower another Beacon program into a symbolic CLR plan:

```bash
dotnet run --project ./Beacon.Compiler/Beacon.Compiler.csproj -- ./compiler/compiler.beacon --stage1 ./examples/stage1-target.beacon
```

To assemble and execute that Beacon-produced plan:

```bash
dotnet run --project ./Beacon.Compiler/Beacon.Compiler.csproj -- ./compiler/compiler.beacon --stage1-run ./examples/stage1-target.beacon
```

The target's lowering decisions are made by `compiler/compiler.beacon`; C# only assembles the returned instruction Records into CLR IL. The included Stage-1 target prints `3` and `true`. See [BOOTSTRAP.md](BOOTSTRAP.md) for the self-hosting roadmap.

---

## Inspect Beacon's core representation

Beacon source is lowered into a canonical representation made only from Atom, List, and Record.

To inspect that representation:

```bash
dotnet run --project ./Beacon.Compiler/Beacon.Compiler.csproj -- ./examples/control-flow.beacon --core
```

For example:

```beacon
ages@i
```

lowers conceptually to:

```text
[index ages i]
```

And:

```beacon
if age > 40 then
    print("old")
else
    print("young")
end
```

lowers conceptually to:

```text
[if [> age 40] [do [call print "old"]] [do [call print "young"]]]
```

The surface syntax can evolve while the structural core remains deliberately small.

---

# Language tour

## Comments

Beacon uses `//` for single-line comments.

```beacon
// A comment
age: number = 42 // comments can follow code
```

---

## Values

### Numbers

```beacon
count: number = 10
price: number = 19.95
```

Beacon currently represents numbers as .NET `double` values.

### Strings

```beacon
name: string = "Beacon"
```

Common escapes are supported:

```beacon
message: string = "hello\nworld"
```

Strings support indexed access and a small set of compiler-friendly operations:

```beacon
first: string = name@0
size: number = name.length()
part: string = name.slice(1, 3)
starts: boolean = name.startsWith("Bea")
```

### Booleans

```beacon
enabled: boolean = true
finished: boolean = false
```

### Null

```beacon
value: null = null
```

---

## Variables

Declarations use one consistent form:

```text
name: type = value
```

Examples:

```beacon
age: number = 42
name: string = "Ada"
active: boolean = true
ages: list = [24, 55, 9, 17, 49]
```

Variables can be reassigned:

```beacon
age = 43
```

Compound addition assignment is supported:

```beacon
age += 1
```

### Explicit typing

Beacon has no `any` type. Every declaration and function parameter must name the type of value it accepts.

When a value legitimately accepts more than one shape, use an explicit union:

```beacon
display: fn(value: number | string) = print(value)

inspectCore: fn(node: atom | list | record) = kind(node)
```

Useful structural types include:

```text
atom      number, string, boolean, null, or symbol
symbol    a Beacon symbol Atom
list      ordered structure
record    named structure
null      the null Atom
fn        function
type      Beacon type value
```

A union is checked left-to-right at runtime by the current bootstrap compiler. Static compile-time type analysis is planned as the compiler becomes self-hosting.

---

## Arithmetic

Beacon supports:

```beacon
a + b
a - b
a * b
a / b
```

Normal arithmetic precedence applies:

```beacon
a + b * c
```

is equivalent to:

```beacon
a + (b * c)
```

Parentheses can be used explicitly:

```beacon
(a + b) * c
```

---

## Equality and comparison

Beacon supports:

```beacon
a == b
a != b
a < b
a <= b
a > b
a >= b
```

Equality for ordinary Beacon Lists and Records is structural rather than CLR reference equality.


Logical expressions use `and`, `or`, and `not`:

```beacon
if active and not finished then
    print("working")
end
```

---

## Lists

Lists represent ordered values and require commas:

```beacon
ages: list = [24, 55, 9, 17, 49]
```

Multiline Lists use the same rule:

```beacon
values: list = [
    10,
    20,
    30
]
```

### List access

Beacon uses `@` for zero-based indexing:

```beacon
first: number = ages@0
current: number = ages@i
next: number = ages@(i + 1)
```

`@` binds tightly, so:

```beacon
ages@i + 1
```

means:

```text
(ages@i) + 1
```

### List length

Lists expose `length()`:

```beacon
count: number = ages.length()
```

Lists also support the bootstrap-oriented collection operations `append()` and `concat()`:

```beacon
ages.append(61)
more: list = ages.concat([72, 80])
ages@0 = 25
```

---

## Records

Records represent named structure:

```beacon
person: record = {
    name: "Ada"
    age: 42
}
```

Access fields with `.`:

```beacon
print(person.name)
print(person.age)
```

Dynamic keys use `@`:

```beacon
field: string = "name"
print(person@field)
person@field = "Grace"
print(person.has("age"))
print(person.keys())
```

Records may also use commas:

```beacon
person: record = {
    name: "Ada",
    age: 42
}
```

---

## Functions

Functions are declared with `fn`:

```beacon
square: fn(x: number) = x * x
```

Parameters are typed:

```beacon
add: fn(a: number, b: number) = a + b
```

Call them normally:

```beacon
print(square(12))
print(add(10, 20))
```

### Multi-expression functions

A List can be used as an ordered function body:

```beacon
incrementTwice: fn(value: number) = [
    value += 1,
    value += 1,
    value
]
```

The final expression is the function's result.

```beacon
incrementTwice(1)
```

returns:

```text
3
```

Beacon does not need a separate fundamental `Block` structure. A function body is an ordered List evaluated as code.

---

## Types

A type is declared using the same declaration model:

```beacon
person: type = {
    name: string
    age: number
}
```

Types may contain both data and behavior:

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
```

There is intentionally no separate `properties` or `methods` section.

Functions are values, so behavior can live alongside data in the same named structure.

### Creating a typed value

```beacon
ada: person = {
    name: "Ada"
    age: 42
}
```

Then:

```beacon
print(ada.name)
print(ada.greet("Hello"))
```

---

## Receiver-relative members

Inside behavior defined on a type, a leading `.` refers to the current receiver:

```beacon
.age
.name
```

For example:

```beacon
birthday: fn() = [
    .age += 1,
    .age
]
```

When called as:

```beacon
ada.birthday()
```

`.age` refers to `ada.age`.

This provides concise receiver-aware behavior without requiring an explicit `self` parameter in source code.

---

## String interpolation

Strings may interpolate variables:

```beacon
name: string = "Ada"
print("Hello, {name}")
```

Inside receiver behavior:

```beacon
greet: fn() = "Hello, I'm {.name}"
```

Current interpolation supports identifiers and receiver-relative members.

---

## Conditionals

Beacon conditionals use explicit boundaries:

```beacon
if age > 40 then
    print("{age} is old!")
else
    print("Young!")
end
```

`else` is optional:

```beacon
if age == 42 then
    print("The answer.")
end
```

Beacon uses `then` and `end` deliberately so control-flow structure remains obvious even when the body becomes large or deeply nested.

---

## Iteration

Beacon currently provides a three-part `for` loop:

```beacon
for [i: number = 0, i < ages.length(), i += 1]
    print(ages@i)
loop
```

The three List elements are:

```text
[initializer, condition, step]
```

For example:

```beacon
for [i: number = 0, i < 10, i += 1]
    print(i)
loop
```

Loops can contain conditionals:

```beacon
for [i: number = 0, i < ages.length(), i += 1]
    if ages@i >= 18 then
        print(ages@i, "is an adult age")
    end
loop
```

---

## Printing

`print()` writes values to standard output:

```beacon
print("Hello, Beacon")
print("Age:", 42)
```

---

# Why Atom / List / Record?

Beacon's central design constraint is that the language should have a very small structural vocabulary.

An Atom represents a value or symbol:

```text
42
"Beacon"
true
age
```

A List represents ordered structure:

```text
[1 2 3]
```

A Record represents named structure:

```text
{name: "Ada" age: 42}
```

Compiler forms use those same structures.

A call:

```beacon
square(12)
```

can be represented as:

```text
[call square 12]
```

A comparison:

```beacon
age > 40
```

can be represented as:

```text
[> age 40]
```

A conditional can be represented as:

```text
[if condition [do ...] [do ...]]
```

This is inspired by the structural simplicity of Lisp while allowing Beacon to use a more conventional, object-friendly surface syntax.

The long-term goal is for code itself to remain naturally inspectable and transformable without forcing programmers to write raw S-expressions.

---

# How Beacon compiles

Beacon currently uses this pipeline:

```text
Beacon source
    |
    v
Lexer / Parser
    |
    v
Atom / List / Record core
    |
    v
IL compiler
    |
    v
CLR Common Intermediate Language
    |
    v
.NET JIT
    |
    v
execution
```

The compiler is currently bootstrapped in C#.

Beacon **does not generate C# source code**. The compiler emits CLR instructions directly using `System.Reflection.Emit`.

The emitted IL handles program control flow, declarations, calls, loops, branching, List and Record construction, indexing, and other language operations.

A small C# runtime currently provides dynamic Beacon operations such as value checking, structural equality, member lookup, indexing, interpolation, and arithmetic dispatch.

---

# Project status

Beacon is a language experiment and should currently be considered **pre-alpha**. The current bootstrap work is moving compiler policy from C# into Beacon itself.

The goal of the compiler today is to validate the language model and syntax before committing to broader language and tooling features.

## Implemented

- Atom / List / Record canonical representation
- direct CLR IL compilation
- Stage-1 Beacon compiler planning plus host plan assembly
- numbers, strings, booleans, and null
- typed variable declarations with no untyped escape hatch
- explicit union types such as `atom | list | record`
- reassignment and `+=`
- arithmetic
- equality and comparison
- Lists
- zero-based List access with `@`
- `length()` on Lists
- Records
- functions
- multi-expression function bodies
- custom types
- receiver-relative behavior
- string interpolation
- `if / else / end`
- `for [...] / loop`
- `print()`
- `kind()` and `fail()` bootstrap primitives
- `and`, `or`, and `not`
- List `append()` / `concat()` and indexed assignment
- String indexing / `slice()` / `startsWith()`
- Record keyed access / `keys()` / `has()`
- Stage-1 compiler execution over canonical Atom/List/Record Core

## Not implemented yet

- standalone `.dll` / `.exe` output
- modules and imports
- package management
- compile-time static type checking
- exceptions in Beacon syntax
- async / concurrency
- generics
- inheritance
- pattern matching
- macros / code transformation
- `quote` / runtime code evaluation
- language server / editor tooling

---

# Repository layout

```text
Beacon.Compiler/
    Beacon.Compiler.csproj
    Program.cs

compiler/
    compiler.beacon

examples/
    hello.beacon
    control-flow.beacon
    bootstrap-primitives.beacon
    stage1-target.beacon

BOOTSTRAP.md
README.md
```

The compiler is intentionally kept small while the language is still evolving.

---

# Compiler commands

Build:

```bash
dotnet build ./Beacon.Compiler/Beacon.Compiler.csproj
```

Run a program:

```bash
dotnet run --project ./Beacon.Compiler/Beacon.Compiler.csproj -- ./examples/control-flow.beacon --run
```

Inspect the canonical Atom/List/Record representation:

```bash
dotnet run --project ./Beacon.Compiler/Beacon.Compiler.csproj -- ./examples/control-flow.beacon --core
```

Compile to in-memory IL without invoking the generated program:

```bash
dotnet run --project ./Beacon.Compiler/Beacon.Compiler.csproj -- ./examples/control-flow.beacon
```

---

# Direction

Beacon is exploring a language that combines:

- Lisp-like structural simplicity
- explicit, readable syntax
- first-class ordered and named data
- object-friendly behavior
- a small semantic core
- direct CLR compilation
- eventual self-hosting

A guiding rule for the language is:

> If Atom, List, or Record can already express a concept cleanly, Beacon should avoid inventing another fundamental structure for it.

Beacon should grow through composition before it grows through new primitives.

---

## License

No license has been selected yet.

If you intend to redistribute, publish, or accept external contributions to Beacon, add a license before doing so.
