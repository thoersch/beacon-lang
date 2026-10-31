---
title: Syntax tour
description: A practical tour of Beacon syntax and core language concepts.
---

This page is a working tour of Beacon's surface syntax. It is meant to help you read and write normal Beacon code without turning the docs into a formal language specification.

## Comments

Beacon uses `//` line comments:

```beacon
// This is a comment
name: string = "Beacon"
```

## Declarations and types

Declarations put the name first, followed by a type and a value:

```beacon
age: number = 42
name: string = "Ada"
active: boolean = true
values: list = [1, 2, 3]
```

Beacon has no `any` type. When a value can have more than one type, use an explicit union:

```beacon
node: atom | list | record | null = null
```

Common types include:

```text
number
string
boolean
list
record
atom
symbol
null
fn
type
```

## Strings and interpolation

Strings use double quotes:

```beacon
name: string = "Ada"
```

Interpolation uses braces:

```beacon
print("Hello, {name}")
```

Inside type behavior, receiver fields can be interpolated directly:

```beacon
"Hi, I'm {.name}"
```

## Functions

A single-expression function can stay on one line:

```beacon
square: fn(value: number) = value * value
```

A multi-expression function body is a List. Commas separate the top-level expressions and the final expression becomes the result:

```beacon
incrementTwice: fn(value: number) = [
    value += 1,
    value += 1,
    value
]
```

Beacon also supports ordered function clauses:

```beacon
format: fn = [
    fn(value: string) = "text: {value}",
    fn(value: number) = "number: {value}"
]
```

Clauses are checked from top to bottom. The first matching clause executes.

## Lists

Lists are ordered and require commas:

```beacon
values: list = [10, 20, 30]
```

Positional access uses `@`:

```beacon
print(values@0)
print(values@2)
```

The index can be an expression:

```beacon
print(values@(i + 1))
```

Useful List methods live directly on the List:

```beacon
values.push(40)
last: number = values.pop()
first: number = values.head()
rest: list = values.tail()
```

`map` and `filter` return new Lists:

```beacon
double: fn(value: number) = value * 2
large: fn(value: number) = value >= 20

print(values.map(double))
print(values.filter(large))
```

`@` is exclusively List indexing. Records and Strings do not use positional `@` access.

## Records

Records are named structures:

```beacon
person: record = {
    name: "Ada"
    age: 42
}
```

Named members use `.`:

```beacon
print(person.name)
print(person.age)
```

When the field name is data rather than a statically known member, use explicit Record operations:

```beacon
field: string = "name"

print(person.get(field))
person.set(field, "Grace")
```

Record field order is not part of the value's meaning.

## Types

A named type describes a Record shape:

```beacon
person: type = {
    name: string
    age: number
}
```

Create a value of that type with a Record literal:

```beacon
ada: person = {
    name: "Ada"
    age: 42
}
```

Types can also define behavior:

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
```

A leading `.` inside type behavior refers to the current receiver:

```beacon
.name
.age
.age += 1
```

## Conditionals

Beacon uses explicit `then`, `else`, and `end` keywords:

```beacon
if age >= 18 then
    print("adult")
else
    print("minor")
end
```

The `else` branch is optional:

```beacon
if active then
    print("ready")
end
```

`if` is also an expression. The selected branch produces the value of its final expression:

```beacon
status: string =
    if active then
        "ready"
    else
        "waiting"
    end
```

An `if` without `else` produces `null` when its condition is false.

Use `else if` for a flat conditional chain. A chain still closes with a single `end`:

```beacon
category: string =
    if age < 13 then
        "child"
    else if age < 18 then
        "teen"
    else if age < 65 then
        "adult"
    else
        "senior"
    end
```

For several ordered predicates, `when` provides a cond-style expression. Conditions are checked from top to bottom and the first true clause wins. Every `when` requires an `otherwise` fallback:

```beacon
category: string =
    when
        age < 13 then
            "child"
        age < 18 then
            "teen"
        age < 65 then
            "adult"
        otherwise
            "senior"
    end
```

Clause bodies can contain multiple expressions. Their final expression becomes the value of that clause:

```beacon
message: string =
    when
        score >= 90 then
            prefix: string = "excellent"
            prefix + " result"
        score >= 70 then
            "good result"
        otherwise
            "keep going"
    end
```

`when` is predicate-based control flow, not pattern matching. It lowers to ordinary conditional Core rather than introducing a new fundamental structural form.

## Loops

Beacon's `for` loop uses a three-part header:

```beacon
for [i: number = 0, i < values.length(), i += 1]
    print(values@i)
loop
```

The three entries are initialization, condition, and step. Commas are required in the header.

Use `break` and `continue` inside loops:

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

`continue` runs the loop step before the condition is checked again.

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

Assignment:

```text
=  +=
```

Unary negation is supported:

```beacon
x: number = -1
y: number = -x
z: number = -(x + 5)
```

## Multiline expressions

A newline can follow an operator when the expression clearly continues:

```beacon
result: number =
    1 +
    2 *
    3
```

Logical expressions can continue the same way:

```beacon
valid: boolean =
    age >= 18 and
    active
```

The operator stays on the preceding line. A newline before an operator remains a statement boundary.

## Includes

Local Beacon files use quoted includes:

```beacon
include "person"
include "models/address"
```

The `.beacon` extension is omitted. Local includes resolve relative to the file containing them.

Standard-library modules use dotted includes:

```beacon
include std.text
include std.math
include std.fs
include std.path
```

Standard-library APIs are namespaced:

```beacon
include std.text
include std.math

clean: string = text.trim("  Beacon  ")
root: number = math.sqrt(81)
```

## The structural model

Beacon's canonical representation is intentionally small:

- **Atom** — a literal or symbol
- **List** — ordered structure
- **Record** — named structure

Higher-level language constructs reduce to combinations of those structures rather than continuously adding new fundamental Core shapes.

That structural simplicity is an important part of Beacon's design, but you do not need to understand the compiler internals to write ordinary Beacon programs.

## Keep exploring

The `examples/` directory in the repository contains runnable programs covering control flow, conditional expressions, function clauses, List methods, multiline expressions, and the standard library.
