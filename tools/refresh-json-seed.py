from pathlib import Path
import re
import sys


def patch_beacon() -> None:
    json_path = Path("std/json.beacon")
    text = json_path.read_text()
    old = '        otherwise "\\\\u00" + _jsonHexDigit((code - code % 16) / 16) + _jsonHexDigit(code % 16)'
    new = '''        otherwise
            if code < 16 then
                "\\\\u000" + _jsonHexDigit(code)
            else
                "\\\\u001" + _jsonHexDigit(code - 16)
            end'''
    if old not in text:
        raise SystemExit("Expected temporary control-escape expression was not found")
    text = text.replace(old, new, 1)

    # Beacon when-clause bodies are blocks. Normalize the compact temporary
    # clauses used while drafting std.json into canonical multiline syntax.
    text = re.sub(
        r'^(\s+)(?!if\b|else if\b)(.+\bthen) (.+)$',
        lambda match: f"{match.group(1)}{match.group(2)}\n{match.group(1)}    {match.group(3)}",
        text,
        flags=re.M,
    )
    text = re.sub(
        r'^(\s+)otherwise (.+)$',
        lambda match: f"{match.group(1)}otherwise\n{match.group(1)}    {match.group(2)}",
        text,
        flags=re.M,
    )
    json_path.write_text(text)

    emitter_path = Path("compiler/emitter.beacon")
    text = emitter_path.read_text()
    anchor = '''    if not handled and kind(callee) == "symbol" and callee.name == "hostEnvironment" then
        result = args@0
        result.push({ op: "call", arg: "Runtime.HostEnvironment" })
        handled = true
    end,
'''
    addition = anchor + '''    if not handled and kind(callee) == "symbol" and callee.name == "hostCharacter" then
        result = args@0
        result.push({ op: "call", arg: "Runtime.HostCharacter" })
        handled = true
    end,
'''
    if anchor not in text:
        raise SystemExit("Expected hostEnvironment emitter block was not found")
    emitter_path.write_text(text.replace(anchor, addition, 1))


def patch_else_if_parser(text: str) -> str:
    pattern = re.compile(
        r'''    private Core ParseIf\(\)\n    \{\n.*?\n    \}\n\n    private Core ParseFor\(\)''',
        re.S,
    )
    if len(list(pattern.finditer(text))) != 1:
        raise SystemExit("Expected exactly one ParseIf block")
    replacement = '''    private Core ParseIf()\n    {\n        ConsumeIdentifier("if", "Expected 'if'");\n        var conditions = new List<Core>();\n        var bodies = new List<Core>();\n        Core elseBody = new ListCore(new List<Core> { Atom.Symbol("do") });\n\n        ParseIfClause(conditions, bodies);\n\n        var chaining = true;\n        while (chaining && MatchIdentifier("else"))\n        {\n            if (MatchIdentifier("if"))\n            {\n                ParseIfClause(conditions, bodies);\n            }\n            else\n            {\n                RequireNewLine("Expected newline after 'else'");\n                elseBody = ParseStatementsUntil("end");\n                chaining = false;\n            }\n        }\n\n        ConsumeIdentifier("end", "Expected 'end' to close if");\n\n        Core result = CoreForms.Form("if", conditions[^1], bodies[^1], elseBody);\n        for (var i = conditions.Count - 2; i >= 0; i--)\n        {\n            result = CoreForms.Form(\n                "if",\n                conditions[i],\n                bodies[i],\n                new ListCore(new List<Core> { Atom.Symbol("do"), result }));\n        }\n        return result;\n    }\n\n    private void ParseIfClause(List<Core> conditions, List<Core> bodies)\n    {\n        var condition = ParseExpression();\n        ConsumeIdentifier("then", "Expected 'then' after if condition");\n        RequireNewLine("Expected newline after 'then'");\n        conditions.Add(condition);\n        bodies.Add(ParseStatementsUntil("else", "end"));\n    }\n\n    private Core ParseFor()'''
    return pattern.sub(replacement, text, count=1)


def patch_seed() -> None:
    path = Path("tools/seed-refresh/Beacon.Compiler/Program.cs")
    text = patch_else_if_parser(path.read_text())

    anchor = "    private static string PathArgument(object? value, string functionName) =>\n"
    method = '''    public static string HostCharacter(object? value)\n    {\n        if (value is not double number || number != Math.Truncate(number) ||\n            number < 0 || number > 0x10FFFF || (number >= 0xD800 && number <= 0xDFFF))\n            throw new Exception("hostCharacter() expects a valid Unicode scalar Number");\n        return char.ConvertFromUtf32((int)number);\n    }\n\n'''
    if text.count(anchor) != 1:
        raise SystemExit("Expected one Runtime PathArgument anchor")
    text = text.replace(anchor, method + anchor, 1)

    lines = text.splitlines()
    updated = []
    count = 0
    for line in lines:
        updated.append(line)
        if "private static readonly " in line and "NumberMethod = Method(nameof(Runtime.Number), typeof(object));" in line:
            updated.append(line.replace("NumberMethod", "HostCharacterMethod").replace("Runtime.Number", "Runtime.HostCharacter"))
            count += 1
    if count != 2:
        raise SystemExit(f"Expected two Number MethodInfo anchors, found {count}")
    text = "\n".join(updated) + "\n"

    resolver = '        "Runtime.Number" => NumberMethod,\n'
    if text.count(resolver) != 1:
        raise SystemExit("Expected one Runtime.Number resolver entry")
    text = text.replace(resolver, resolver + '        "Runtime.HostCharacter" => HostCharacterMethod,\n', 1)

    call_pattern = re.compile(
        r'''(        if \(callee is Atom \{ Kind: AtomKind\.Symbol \} numberAtom && numberAtom\.Text == "number"\)\n        \{\n.*?            return;\n        \}\n)''',
        re.S,
    )
    matches = list(call_pattern.finditer(text))
    if len(matches) != 1:
        raise SystemExit(f"Expected one direct number() call block, found {len(matches)}")
    host_call = '''\n        if (callee is Atom { Kind: AtomKind.Symbol } hostCharacterAtom && hostCharacterAtom.Text == "hostCharacter")\n        {\n            if (args.Length != 1) throw new Exception("hostCharacter() expects one argument");\n            EmitExpr(args[0], ctx);\n            ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, HostCharacterMethod);\n            return;\n        }\n'''
    text = call_pattern.sub(lambda match: match.group(1) + host_call, text, count=1)
    path.write_text(text)


if len(sys.argv) != 2 or sys.argv[1] not in {"beacon", "seed"}:
    raise SystemExit("usage: refresh-json-seed.py beacon|seed")

if sys.argv[1] == "beacon":
    patch_beacon()
else:
    patch_seed()
