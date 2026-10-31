# Syntax

Beacon uses a small, explicit surface syntax that lowers into a compact structural Core built from Atoms, Lists, and Records.

## Declarations and types

Declarations name a value and state its type explicitly:

```beacon
age: number = 42
name: string = "Ada"
active: boolean = true
values: list = [1, 2, 3]
```

Beacon has no `any` type. Use an explicit type or union instead:

```beacon
node: atom | list | record | null = null
```

Common built-in types include:

- `number`
- `string`
- `boolean`
- `list`
- `record`
- `atom`
- `symbol`
- `null`
- `fn`
- `type`

## Strings

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

A function can be a single expression:

```beacon
square: fn(value: number) = value * value
```

A multi-expression function body uses a List. Commas separate the top-level expressions, and the final expression is the function result:

```beacon
incrementTwice: fn(value: number) = [
    value += 1,
    value += 1,
    value
]
```

Functions are ordinary values.

### Function clauses

A function binding can contain an ordered List of typed clauses:

```beacon
format: fn = [
    fn(value: string) = "text: {value}",
    fn(value: number) = "number: {value}"
]
```

Clauses are checked from top to bottom. The first clause whose arity and parameter types match is called.

Union types and named Beacon types participate in clause matching. Return types do not participate in dispatch.

## Lists

Lists are ordered and require commas between elements:

```beacon
values: list = [10, 20, 30]
```

Use `@` for positional List access:

```beacon
print(values@0)
values@1 = 42
print(values@(i + 1))
```

`@` is List-only. Records use named access, and Strings use String methods such as `slice()`.

Common List methods include:

```beacon
values.push(40)
last: number = values.pop()
doubled: list = values.map(double)
selected: list = values.filter(isPositive)
first: number = values.head()
rest: list = values.tail()
```

`map()` and `filter()` return new Lists. `push()` and `pop()` mutate the receiver.

## Records

Records are named structure:

```beacon
person: record = {
    name: "Ada"
    age: 42
}
```

Use dot notation for static named access:

```beacon
print(person.name)
print(person.age)
```

For dynamic field names, use `get()` and `set()`:

```beacon
field: string = "name"
print(person.get(field))
person.set(field, "Grace")
```

Record field order is not part of the Record's meaning.

## Named types

Define a named type with `type`:

```beacon
person: type = {
    name: string
    age: number
}
```

Then construct values of that type with ordinary Record syntax:

```beacon
ada: person = {
    name: "Ada"
    age: 42
}
```

Types can define behavior:

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

A leading `.` inside type behavior refers to the current receiver.

## Includes

Local includes are relative to the containing file and omit the `.beacon` extension:

```beacon
include "person"
include "models/address"
```

The extension is intentionally omitted. Writing `include "person.beacon"` is rejected.

Standard-library modules use named includes:

```beacon
include std.text
include std.math
include std.fs
include std.path
```

Standard-library APIs remain namespaced:

```beacon
clean: string = text.trim(value)
root: number = math.sqrt(81)
path.writeText("output.txt", "hello")
```

Includes are deduplicated, and circular includes are rejected.

## Control flow

Use `if`, `else`, and `end` for conditional control flow:

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

Flattened `else if` is the canonical Beacon style. When an `else` continues immediately with another condition, write `else if` on one line rather than nesting an `if` beneath `else`.

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

`break` and `continue` apply to the innermost loop. A function declared inside a loop cannot break or continue the enclosing loop.

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

Unary numeric negation uses `-`:

```beacon
negative: number = -value
```

## Multiline expressions

An expression can continue on the next line when the preceding token makes continuation unambiguous:

```beacon
result: number =
    1 +
    2 *
    3
```

Logical expressions can be split the same way:

```beacon
endsWith: fn(str: string, search: string) =
    search.length() <= str.length() and
    str.slice(str.length() - search.length(), search.length()) == search
```

Keep the operator on the preceding line. A newline before an operator remains a statement boundary.
