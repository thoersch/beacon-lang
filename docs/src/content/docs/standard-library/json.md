---
title: JSON
description: Parse and serialize JSON with Beacon's std.json module.
---

Beacon's JSON support lives in `std.json` and is implemented in Beacon.

```beacon
include std.json
```

## Parse JSON

`json.parse(source)` converts JSON text into ordinary Beacon values:

```beacon
include std.json

payload: record = json.parse("{\"name\":\"Ada\",\"active\":true,\"scores\":[10,20]}")

print(payload.name)
print(payload.active)
print(payload.scores@0)
```

JSON values map directly to Beacon values:

| JSON | Beacon |
| --- | --- |
| object | `record` |
| array | `list` |
| string | `string` |
| number | `number` |
| `true` / `false` | `boolean` |
| `null` | `null` |

Parsing is strict. Invalid number syntax, malformed escapes, unpaired Unicode surrogates, unescaped control characters, and trailing content fail with an error that includes the character position.

Unicode escapes are supported, including surrogate pairs:

```beacon
print(json.parse("\"\\u0041\\u03a9\""))
print(json.parse("\"\\uD83D\\uDE03\""))
```

## Serialize JSON

`json.stringify(value)` produces compact JSON:

```beacon
include std.json

payload: record = {
    name: "Ada"
    active: true
    values: [1, 2, null]
}

print(json.stringify(payload))
```

Output:

```text
{"name":"Ada","active":true,"values":[1,2,null]}
```

Strings are escaped as required by JSON. Lists and Records can be nested freely.

`json.stringify()` rejects values JSON cannot represent, including Beacon Symbols, functions, types, non-finite Numbers, and cyclic List or Record structures.

## Runtime boundary

The parser and serializer are Beacon code. Stage-0 exposes only `hostCharacter(number)`, a small Unicode-scalar-to-String primitive needed to decode JSON Unicode escapes. JSON grammar, validation, escaping, parsing, and serialization remain in `std/json.beacon`.
