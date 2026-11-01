from pathlib import Path
import re


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one match, found {count}: {old[:80]!r}")
    p.write_text(text.replace(old, new, 1))


# Parser: metadata is parsed only on named declarations, with private restricted
# to module-level declarations. The metadata is attached to the def node so it
# remains declaration visibility rather than runtime function state.
replace_once(
    "compiler/parser.beacon",
    "        expressions.push(parseStatement(state))\n",
    "        expressions.push(parseTopLevelStatement(state))\n",
)

replace_once(
    "compiler/parser.beacon",
    "parseStatement: fn(state: record) = [\n",
    '''parseTopLevelStatement: fn(state: record) = [
    result: atom | list | record = null,
    if checkToken(state, "identifier") and checkNextToken(state, "colon") then
        result = parseDeclaration(state, true)
    else
        result = parseStatement(state)
    end,
    result
]

parseStatement: fn(state: record) = [
''',
)

replace_once(
    "compiler/parser.beacon",
    '''    else if checkToken(state, "identifier") and checkNextToken(state, "colon") then
        result = parseDeclaration(state)
''',
    '''    else if checkToken(state, "identifier") and checkNextToken(state, "colon") then
        result = parseDeclaration(state, false)
''',
)

replace_once(
    "compiler/parser.beacon",
    "        initializer = parseDeclaration(state)\n",
    "        initializer = parseDeclaration(state, false)\n",
)

old_decl = '''parseDeclaration: fn(state: record) = [
    nameToken: record = consumeToken(state, "identifier", "Expected declaration name"),
    consumeToken(state, "colon", "Expected ':'"),
    result: atom | list | record = null,

    if matchIdentifier(state, "fn") then
        result = [symbol("def"), symbol(nameToken.text), symbol("fn"), parseFunctionDeclarationAfterFn(state)]
    else if matchIdentifier(state, "type") then
        consumeToken(state, "equal", "Expected '=' after type declaration")
        result = [symbol("def"), symbol(nameToken.text), symbol("type"), parseTypeDefinition(state)]
    else
        typeName: string = parseTypeAnnotation(state)
        consumeToken(state, "equal", "Expected '=' in declaration")
        skipNewLines(state)
        result = [symbol("def"), symbol(nameToken.text), symbol(typeName), parseExpression(state)]
    end,

    result
]
'''

new_decl = '''parseFunctionMetadataAfterFn: fn(state: record) = [
    metadata: record = {},

    if matchToken(state, "less") then
        if checkToken(state, "greater") then
            token: record = currentToken(state)
            fail("Function metadata cannot be empty at " + token.line + ":" + token.column)
        end

        done: boolean = false
        for [tick: number = 0, not done, tick += 1]
            tag: record = consumeToken(state, "identifier", "Expected function metadata name")
            if tag.text != "private" then
                fail("Unknown function metadata '" + tag.text + "' at " + tag.line + ":" + tag.column)
            end
            if metadata.has(tag.text) then
                fail("Duplicate function metadata '" + tag.text + "' at " + tag.line + ":" + tag.column)
            end
            metadata.set(tag.text, true)

            if matchToken(state, "comma") then
                if checkToken(state, "greater") then
                    token: record = currentToken(state)
                    fail("Expected function metadata name after ',' at " + token.line + ":" + token.column)
                end
            else
                done = true
            end
        loop

        consumeToken(state, "greater", "Expected '>' after function metadata")
    end,

    metadata
]

parseDeclaration: fn(state: record, moduleLevel: boolean) = [
    nameToken: record = consumeToken(state, "identifier", "Expected declaration name"),
    consumeToken(state, "colon", "Expected ':'"),
    result: atom | list | record = null,

    if matchIdentifier(state, "fn") then
        metadata: record = parseFunctionMetadataAfterFn(state)
        if metadata.has("private") and not moduleLevel then
            fail("fn<private> is only valid on module-level named function declarations at " + nameToken.line + ":" + nameToken.column)
        end

        result = [symbol("def"), symbol(nameToken.text), symbol("fn"), parseFunctionDeclarationAfterFn(state)]
        if metadata.has("private") then
            result.push(metadata)
        end
    else if matchIdentifier(state, "type") then
        consumeToken(state, "equal", "Expected '=' after type declaration")
        result = [symbol("def"), symbol(nameToken.text), symbol("type"), parseTypeDefinition(state)]
    else
        typeName: string = parseTypeAnnotation(state)
        consumeToken(state, "equal", "Expected '=' in declaration")
        skipNewLines(state)
        result = [symbol("def"), symbol(nameToken.text), symbol(typeName), parseExpression(state)]
    end,

    result
]
'''
replace_once("compiler/parser.beacon", old_decl, new_decl)

replace_once(
    "compiler/parser.beacon",
    '''        consumeIdentifier(state, "fn", "Expected fn clause")
        clauses.push(parseFunctionAfterFn(state))
''',
    '''        consumeIdentifier(state, "fn", "Expected fn clause")
        if checkToken(state, "less") then
            token: record = currentToken(state)
            fail("Function metadata is only valid on module-level named function declarations at " + token.line + ":" + token.column)
        end
        clauses.push(parseFunctionAfterFn(state))
''',
)

replace_once(
    "compiler/parser.beacon",
    '''        if matchIdentifier(state, "fn") then
            members.set(nameToken.text, parseFunctionDeclarationAfterFn(state))
''',
    '''        if matchIdentifier(state, "fn") then
            if checkToken(state, "less") then
                token: record = currentToken(state)
                fail("Function metadata is only valid on module-level named function declarations at " + token.line + ":" + token.column)
            end
            members.set(nameToken.text, parseFunctionDeclarationAfterFn(state))
''',
)

# Core: private metadata only changes the exported namespace names. The function
# still executes in the module environment, so private helpers remain callable by
# public functions and other private helpers.
replace_once(
    "compiler/core.beacon",
    '''definitionName: fn(node: atom | list | record) = [
    result: string = "",
    if isForm(node, "def") then
        name: symbol = node@1
        result = name.name
    end,
    result
]
''',
    '''definitionName: fn(node: atom | list | record) = [
    result: string = "",
    if isForm(node, "def") then
        name: symbol = node@1
        result = name.name
    end,
    result
]

definitionIsPrivate: fn(node: atom | list | record) = [
    result: boolean = false,
    if isForm(node, "def") and node.length() > 4 then
        metadata: atom | list | record = node@4
        if kind(metadata) == "record" then
            result = metadata.has("private") and metadata.get("private") == true
        end
    end,
    result
]
''',
)

replace_once(
    "compiler/core.beacon",
    '''        if listContainsString(names, name) then
            fail("Duplicate declaration in standard-library namespace: " + name)
        end
        names.push(name)
''',
    '''        if listContainsString(names, name) then
            fail("Duplicate public declaration in standard-library namespace: " + name)
        end
        if not definitionIsPrivate(node) then
            names.push(name)
        end
''',
)

# A private binding can still conflict with a child namespace internally, so
# collision checks use all definitions, not just the public export list.
replace_once(
    "compiler/core.beacon",
    '''        if listContainsString(exports, key) then
            fail("Standard-library namespace member conflicts with child namespace: " + key)
        end
''',
    '''        if programHasDefinition(body, key) then
            fail("Standard-library namespace member conflicts with child namespace: " + key)
        end
''',
)

replace_once(
    "compiler/emitter.beacon",
    '''        if listContainsString(names, key) then
            fail("Standard-library namespace member conflicts with child namespace: " + key)
        end
''',
    '''        if programHasDefinition(body, key) then
            fail("Standard-library namespace member conflicts with child namespace: " + key)
        end
''',
)

# std.json: remove pseudo-private underscore prefixes and mark implementation
# helpers with real function metadata.
p = Path("std/json.beacon")
text = p.read_text()
suffixes = sorted(set(re.findall(r"\b_json([A-Z][A-Za-z0-9_]*)", text)), key=len, reverse=True)
if not suffixes:
    raise SystemExit("std/json.beacon: no _json helpers found")
renamed = []
for suffix in suffixes:
    old = "_json" + suffix
    new = suffix[0].lower() + suffix[1:]
    text = re.sub(rf"\b{re.escape(old)}\b", new, text)
    renamed.append(new)
for name in renamed:
    text, count = re.subn(rf"(?m)^{re.escape(name)}: fn(?=\()", f"{name}: fn<private>", text)
    if count != 1:
        raise SystemExit(f"std/json.beacon: expected one helper declaration for {name}, found {count}")
if "_json" in text:
    raise SystemExit("std/json.beacon: underscore-prefixed JSON helper remains")
p.write_text(text)

# Syntax docs.
replace_once(
    "docs/src/content/docs/language/syntax.md",
    "Clauses are checked from top to bottom. The first matching clause executes.\n\n## Lists\n",
    '''Clauses are checked from top to bottom. The first matching clause executes.

Function metadata follows `fn` in angle brackets. `private` is currently the only supported metadata tag:

```beacon
parseValue: fn<private>(state: record) = ...
```

Functions are public by default. A `private` function remains callable by other code in the same module, but it is omitted from the namespace created by a named include. Function metadata is valid only on named, module-level function declarations; nested functions, type methods, and individual function clauses cannot carry it. Unknown metadata is a compile-time error.

## Lists
''',
)

# std.json docs make the public surface explicit.
json_doc = Path("docs/src/content/docs/standard-library/json.md")
json_text = json_doc.read_text()
needle = "```beacon\ninclude std.json\n"
if needle not in json_text:
    raise SystemExit("json docs: API example anchor not found")
json_text = json_text.replace(
    needle,
    "Only `parse` and `stringify` are public. Parser and encoder helpers use `fn<private>` and stay inside the `json` module.\n\n" + needle,
    1,
)
json_doc.write_text(json_text)

# VS Code grammar and its surface audit.
grammar = Path("editors/vscode/syntaxes/beacon.tmLanguage.json")
grammar_text = grammar.read_text()
logical = '''        {
          "name": "keyword.control.logical.beacon",
          "match": "\\\\b(and|or|not)\\\\b"
        },
'''
private_rule = logical + '''        {
          "name": "storage.modifier.function.beacon",
          "match": "\\\\bprivate\\\\b"
        },
'''
if grammar_text.count(logical) != 1:
    raise SystemExit("VS Code grammar: logical-keyword anchor not found exactly once")
grammar.write_text(grammar_text.replace(logical, private_rule, 1))

replace_once(
    "editors/vscode/check-syntax.mjs",
    '''    {
        repository: "keywords",
        scope: "keyword.control.logical.beacon",
        tokens: ["and", "or", "not"]
    },
''',
    '''    {
        repository: "keywords",
        scope: "keyword.control.logical.beacon",
        tokens: ["and", "or", "not"]
    },
    {
        repository: "keywords",
        scope: "storage.modifier.function.beacon",
        tokens: ["private"]
    },
''',
)

# Permanent regression coverage for visibility and invalid metadata placement.
workflow = Path(".github/workflows/std-json.yml")
workflow_text = workflow.read_text()
anchor = '''      - name: Reject cyclic values
        shell: bash
        run: |
'''
if workflow_text.count(anchor) != 1:
    raise SystemExit("std.json workflow: cyclic-test anchor not found")
visibility_step = '''      - name: Verify private function metadata
        shell: bash
        run: |
          set -euo pipefail

          cat > /tmp/private-export.beacon <<'EOF'
          include std.json
          json.parseValue
          EOF
          if bash ./beacon.sh /tmp/private-export.beacon >/tmp/private-export.out 2>/tmp/private-export.err; then
            echo 'Expected private std.json helper to be absent from the json namespace' >&2
            exit 1
          fi

          cat > /tmp/private-nested.beacon <<'EOF'
          outer: fn() = [
              helper: fn<private>() = 1,
              helper()
          ]
          outer()
          EOF
          if bash ./beacon.sh /tmp/private-nested.beacon >/tmp/private-nested.out 2>/tmp/private-nested.err; then
            echo 'Expected fn<private> on a nested declaration to fail' >&2
            exit 1
          fi

          cat > /tmp/private-unknown.beacon <<'EOF'
          helper: fn<internal>() = 1
          EOF
          if bash ./beacon.sh /tmp/private-unknown.beacon >/tmp/private-unknown.out 2>/tmp/private-unknown.err; then
            echo 'Expected unknown function metadata to fail' >&2
            exit 1
          fi

'''
workflow.write_text(workflow_text.replace(anchor, visibility_step + anchor, 1))

print("Applied fn<private> metadata support and refactored std.json helpers")
