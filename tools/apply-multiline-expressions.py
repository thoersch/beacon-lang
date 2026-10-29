from pathlib import Path

parser_path = Path("compiler/parser.beacon")
text = parser_path.read_text()

replacements = [
    (
'''            typeName: string = parseTypeAnnotation(state)\n            consumeToken(state, "equal", "Expected '=' in declaration")\n            result = [symbol("def"), symbol(nameToken.text), symbol(typeName), parseExpression(state)]\n''',
'''            typeName: string = parseTypeAnnotation(state)\n            consumeToken(state, "equal", "Expected '=' in declaration")\n            skipNewLines(state)\n            result = [symbol("def"), symbol(nameToken.text), symbol(typeName), parseExpression(state)]\n'''
    ),
    (
'''    if matchToken(state, "pluseq") then\n        result = [symbol("+="), left, parseAssignment(state)]\n    else\n        if matchToken(state, "equal") then\n            result = [symbol("="), left, parseAssignment(state)]\n        end\n''',
'''    if matchToken(state, "pluseq") then\n        skipNewLines(state)\n        result = [symbol("+="), left, parseAssignment(state)]\n    else\n        if matchToken(state, "equal") then\n            skipNewLines(state)\n            result = [symbol("="), left, parseAssignment(state)]\n        end\n'''
    ),
    (
'''    for [more: boolean = matchIdentifier(state, "or"), more, more = matchIdentifier(state, "or")]\n        expression = [symbol("or"), expression, parseAnd(state)]\n    loop,\n''',
'''    for [more: boolean = matchIdentifier(state, "or"), more, more = matchIdentifier(state, "or")]\n        skipNewLines(state)\n        expression = [symbol("or"), expression, parseAnd(state)]\n    loop,\n'''
    ),
    (
'''    for [more: boolean = matchIdentifier(state, "and"), more, more = matchIdentifier(state, "and")]\n        expression = [symbol("and"), expression, parseComparison(state)]\n    loop,\n''',
'''    for [more: boolean = matchIdentifier(state, "and"), more, more = matchIdentifier(state, "and")]\n        skipNewLines(state)\n        expression = [symbol("and"), expression, parseComparison(state)]\n    loop,\n'''
    ),
    (
'''        if active then\n            expression = [symbol(operator), expression, parseAdditive(state)]\n        end\n''',
'''        if active then\n            skipNewLines(state)\n            expression = [symbol(operator), expression, parseAdditive(state)]\n        end\n'''
    ),
    (
'''        if active then\n            expression = [symbol(operator), expression, parseMultiplicative(state)]\n        end\n''',
'''        if active then\n            skipNewLines(state)\n            expression = [symbol(operator), expression, parseMultiplicative(state)]\n        end\n'''
    ),
    (
'''        if active then\n            expression = [symbol(operator), expression, parseUnary(state)]\n        end\n''',
'''        if active then\n            skipNewLines(state)\n            expression = [symbol(operator), expression, parseUnary(state)]\n        end\n'''
    ),
    (
'''    if matchIdentifier(state, "not") then\n        result = [symbol("not"), parseUnary(state)]\n    else\n        if matchToken(state, "minus") then\n            result = [symbol("neg"), parseUnary(state)]\n''',
'''    if matchIdentifier(state, "not") then\n        skipNewLines(state)\n        result = [symbol("not"), parseUnary(state)]\n    else\n        if matchToken(state, "minus") then\n            skipNewLines(state)\n            result = [symbol("neg"), parseUnary(state)]\n'''
    ),
    (
'''            if matchToken(state, "at") then\n                expression = [symbol("index"), expression, parsePrimary(state)]\n''',
'''            if matchToken(state, "at") then\n                skipNewLines(state)\n                expression = [symbol("index"), expression, parsePrimary(state)]\n'''
    ),
    (
'''                        loop\n                    end\n                    consumeToken(state, "rparen", "Expected ')' after arguments")\n''',
'''                        loop\n                    end\n                    skipNewLines(state)\n                    consumeToken(state, "rparen", "Expected ')' after arguments")\n'''
    ),
    (
'''                    if matchToken(state, "lparen") then\n                        result = parseExpression(state)\n                        consumeToken(state, "rparen", "Expected ')'")\n''',
'''                    if matchToken(state, "lparen") then\n                        skipNewLines(state)\n                        result = parseExpression(state)\n                        skipNewLines(state)\n                        consumeToken(state, "rparen", "Expected ')'")\n'''
    ),
]

for old, new in replacements:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one parser match, found {count}: {old[:80]!r}")
    text = text.replace(old, new, 1)

parser_path.write_text(text)

example = '''endsWith: fn(str: string, search: string) =\n    search.length() <= str.length() and\n    str.slice(str.length() - search.length(), search.length()) == search\n\nvalue: number =\n    1 +\n    2 *\n    3\n\nassigned: number = 0\nassigned =\n    40 +\n    2\n\nassigned +=\n    1\n\nnegative: number = -\n    5\n\ngrouped: number = (\n    10 +\n    5\n)\n\nlogical: boolean =\n    false or\n    true and\n    not\n    false\n\nprint(value)\nprint(assigned)\nprint(negative)\nprint(grouped)\n\nif logical and\n    endsWith("Beacon", "con") then\n    print("multiline")\nend\n\nprint(\n    20 +\n    22\n)\n'''
Path("examples/multiline-expressions.beacon").write_text(example)

workflow_path = Path(".github/workflows/compiler.yml")
workflow = workflow_path.read_text()
anchor = '''      - name: Verify unary minus and loop control\n'''
if anchor not in workflow:
    raise SystemExit("Compiler workflow anchor not found")
block = '''      - name: Verify multiline expressions\n        shell: bash\n        run: |\n          output="$(bash ./beacon.sh examples/multiline-expressions.beacon)"\n          printf '%s\\n' "$output"\n          expected=$'7\\n43\\n-5\\n15\\nmultiline\\n42'\n          [[ "$output" == "$expected" ]]\n\n'''
workflow = workflow.replace(anchor, block + anchor, 1)
workflow_path.write_text(workflow)

readme_path = Path("README.md")
readme = readme_path.read_text()
marker = '''## Control flow\n'''
if marker not in readme:
    raise SystemExit("README control-flow section not found")
section = '''## Multiline expressions\n\nA newline may follow an operator when the expression clearly continues. This keeps long expressions readable without introducing a continuation token:\n\n```beacon\nendsWith: fn(str: string, search: string) =\n    search.length() <= str.length() and\n    str.slice(str.length() - search.length(), search.length()) == search\n\nresult: number =\n    1 +\n    2 *\n    3\n```\n\nThe operator stays on the preceding line. A newline before an operator still ends the expression, preserving Beacon's statement boundaries.\n\n'''
readme = readme.replace(marker, section + marker, 1)
readme_path.write_text(readme)
