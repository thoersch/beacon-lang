from pathlib import Path

ROOT = Path('.')


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if old not in text:
        raise SystemExit(f'Expected migration pattern not found in {path}:\n{old[:240]}')
    path.write_text(text.replace(old, new, 1))


# ---------------------------------------------------------------------------
# Beacon parser: one fn binding may contain an ordered List of fn clauses.
# ---------------------------------------------------------------------------
parser = ROOT / 'compiler/parser.beacon'
replace_once(
    parser,
    '''    if matchIdentifier(state, "fn") then\n        result = [symbol("def"), symbol(nameToken.text), symbol("fn"), parseFunctionAfterFn(state)]\n''',
    '''    if matchIdentifier(state, "fn") then\n        result = [symbol("def"), symbol(nameToken.text), symbol("fn"), parseFunctionDeclarationAfterFn(state)]\n''')

replace_once(
    parser,
    '''        if matchIdentifier(state, "fn") then\n            members.set(nameToken.text, parseFunctionAfterFn(state))\n''',
    '''        if matchIdentifier(state, "fn") then\n            members.set(nameToken.text, parseFunctionDeclarationAfterFn(state))\n''')

marker = '''parseFunctionAfterFn: fn(state: record) = [\n'''
text = parser.read_text()
if marker not in text:
    raise SystemExit('parseFunctionAfterFn marker not found')
helpers = '''parseFunctionDeclarationAfterFn: fn(state: record) = [\n    result: list = [],\n\n    if checkToken(state, "lparen") then\n        result = parseFunctionAfterFn(state)\n    else\n        consumeToken(state, "equal", "Expected '(' or '=' after fn")\n        result = parseFunctionClausesAfterEqual(state)\n    end,\n\n    result\n]\n\nparseFunctionClausesAfterEqual: fn(state: record) = [\n    consumeToken(state, "lbracket", "Expected '[' after 'fn ='") ,\n    clauses: list = [symbol("list")],\n    skipNewLines(state),\n\n    if checkToken(state, "rbracket") then\n        fail("Function clause list cannot be empty")\n    end,\n\n    done: boolean = false,\n    for [tick: number = 0, not done, tick += 1]\n        consumeIdentifier(state, "fn", "Expected fn clause")\n        clauses.append(parseFunctionAfterFn(state))\n        skipNewLines(state)\n\n        if matchToken(state, "rbracket") then\n            done = true\n        else\n            consumeToken(state, "comma", "Beacon function clauses require commas between clauses")\n            skipNewLines(state)\n        end\n    loop,\n\n    [symbol("fn"), clauses]\n]\n\n'''
parser.write_text(text.replace(marker, helpers + marker, 1))


# ---------------------------------------------------------------------------
# Beacon emitter: fn clause sets lower to a single fn.clauses plan operation.
# The clause set remains Lists/Records all the way to the runtime boundary.
# ---------------------------------------------------------------------------
emitter = ROOT / 'compiler/emitter.beacon'
old_emit = '''emitFunction: fn(node: list) = [\n    rawParams: list = node@1,\n    params: list = [],\n\n    for [i: number = 0, i < rawParams.length(), i += 1]\n        parameter: record = rawParams@i\n        paramName: symbol = parameter.name\n        paramType: symbol = parameter.type\n        params.append({ name: paramName.name, type: paramType.name })\n    loop,\n\n    [{\n        op: "fn",\n        params: params,\n        body: emitFunctionBody(node@2)\n    }]\n]\n'''
new_emit = '''emitFunctionClauses: fn(node: list) = [\n    clauseValues: list = node@1,\n    clauses: list = [],\n\n    for [i: number = 1, i < clauseValues.length(), i += 1]\n        clause: list = clauseValues@i\n        if not isForm(clause, "fn") or clause.length() != 3 then\n            fail("Function clause must be a function")\n        end\n\n        rawParams: list = clause@1\n        parameterTypes: list = []\n        for [p: number = 0, p < rawParams.length(), p += 1]\n            parameter: record = rawParams@p\n            paramType: symbol = parameter.type\n            parameterTypes.append(paramType.name)\n        loop\n\n        clauses.append({\n            value: emitFunction(clause)\n            types: parameterTypes\n        })\n    loop,\n\n    [{ op: "fn.clauses", clauses: clauses }]\n]\n\nemitFunction: fn(node: list) = [\n    result: list = [],\n\n    if node.length() == 2 then\n        result = emitFunctionClauses(node)\n    else\n        rawParams: list = node@1\n        params: list = []\n\n        for [i: number = 0, i < rawParams.length(), i += 1]\n            parameter: record = rawParams@i\n            paramName: symbol = parameter.name\n            paramType: symbol = parameter.type\n            params.append({ name: paramName.name, type: paramType.name })\n        loop\n\n        result = [{\n            op: "fn",\n            params: params,\n            body: emitFunctionBody(node@2)\n        }]\n    end,\n\n    result\n]\n'''
replace_once(emitter, old_emit, new_emit)


# ---------------------------------------------------------------------------
# Documentation and executable example.
# ---------------------------------------------------------------------------
readme = ROOT / 'README.md'
replace_once(
    readme,
    '''Multiple expressions use a List; the final expression is the result:\n\n```beacon\nincrementTwice: fn(x: number) = [\n    x += 1,\n    x += 1,\n    x\n]\n```\n''',
    '''Multiple expressions use a List; the final expression is the result:\n\n```beacon\nincrementTwice: fn(x: number) = [\n    x += 1,\n    x += 1,\n    x\n]\n```\n\nA function may also be defined as an ordered List of matching clauses:\n\n```beacon\nformat: fn = [\n    fn(value: string) = "text: {value}",\n    fn(value: number) = "number: {value}"\n]\n```\n\nFunction clauses are pattern matching, not ranked overload resolution. Beacon tries clauses from top to bottom and executes the first clause whose arity and parameter types match the arguments. Union and named types participate in the same type matching rules. Return types never participate in dispatch.\n\nBecause clause order is semantic, broader patterns can deliberately precede narrower ones:\n\n```beacon\nclassify: fn = [\n    fn(value: atom) = "atom",\n    fn(value: string) = "string"\n]\n\nprint(classify("Beacon")) // atom\n```\n\nThe declaration remains one binding named `format`; the clause List is part of the function's program structure rather than a set of repeated declarations.\n''')

example = ROOT / 'examples/function-clauses.beacon'
example.write_text('''describe: fn = [\n    fn(value: string) = "string",\n    fn(value: number) = "number"\n]\n\npick: fn = [\n    fn(value: atom) = "atom",\n    fn(value: string) = "string"\n]\n\nsliceText: fn = [\n    fn(value: string, start: number) = value.slice(start),\n    fn(value: string, start: number, length: number) = value.slice(start, length)\n]\n\nformatter: type = {\n    prefix: string\n    render: fn = [\n        fn(value: string) = "{.prefix}:{value}",\n        fn(value: number) = "{.prefix}:number"\n    ]\n}\n\nperson: type = {\n    name: string\n}\n\ndescribePerson: fn = [\n    fn(value: person) = "person",\n    fn(value: record) = "record"\n]\n\nscalar: fn = [\n    fn(value: string | number) = "scalar",\n    fn(value: atom) = "atom"\n]\n\nf: formatter = { prefix: "value" }\nada: person = { name: "Ada" }\n\nprint(kind(describe))\nprint(describe("Beacon"))\nprint(describe(42))\nprint(pick("Beacon"))\nprint(sliceText("Beacon", 2))\nprint(sliceText("Beacon", 1, 3))\nprint(f.render("Ada"))\nprint(f.render(42))\nprint(describePerson(ada))\nprint(scalar(42))\n''')


# ---------------------------------------------------------------------------
# Permanent CI regression coverage.
# ---------------------------------------------------------------------------
workflow = ROOT / '.github/workflows/compiler.yml'
workflow_text = workflow.read_text()
append = '''\n      - name: Verify ordered function clauses\n        shell: bash\n        run: |\n          output="$(bash ./beacon.sh examples/function-clauses.beacon)"\n          printf '%s\\n' "$output"\n\n          expected=$'fn\\nstring\\nnumber\\natom\\nacon\\neac\\nvalue:Ada\\nvalue:number\\nperson\\nscalar'\n          [[ "$output" == "$expected" ]]\n\n          cat > /tmp/no-function-clause.beacon <<'BEACON'\n          onlyNumber: fn = [\n              fn(value: number) = value\n          ]\n          print(onlyNumber("Beacon"))\n          BEACON\n\n          set +e\n          no_match="$(bash ./beacon.sh /tmp/no-function-clause.beacon 2>&1)"\n          status=$?\n          set -e\n          [[ $status -ne 0 ]]\n          grep -F 'No matching function clause for (string)' <<<"$no_match"\n\n          cat > /tmp/legacy-function.beacon <<'BEACON'\n          twice: fn(value: number) = value * 2\n          print(twice(21))\n          BEACON\n          [[ "$(bash ./beacon.sh /tmp/legacy-function.beacon)" == '42' ]]\n'''
if 'Verify ordered function clauses' in workflow_text:
    raise SystemExit('Function-clause CI already exists')
workflow.write_text(workflow_text.rstrip() + '\n' + append)


# ---------------------------------------------------------------------------
# Temporary Stage-0 seed source. The input source is the exact seed-refresh
# source used for the List-only indexing migration and already has those
# semantics. This patch adds only the runtime function-clause boundary.
# ---------------------------------------------------------------------------
seed = ROOT / 'tools/seed-refresh/Beacon.Compiler/Program.cs'
if seed.exists():
    seed_text = seed.read_text()

    if 'BFnClauses' in seed_text:
        raise SystemExit('Seed already contains function clause support')
    if '@ requires a List on the left' not in seed_text:
        raise SystemExit('Seed source is not the expected List-only baseline')
    if 'RecordGet' not in seed_text or 'RecordSet' not in seed_text:
        raise SystemExit('Seed source is missing explicit Record get/set semantics')

    seed_text = seed_text.replace(
        '''public sealed class BRecord : Dictionary<string, object?> { }\n''',
        '''public sealed record BFnClause(BFn Function, string[] ParameterTypes);\n\npublic sealed class BFnClauses\n{\n    public IReadOnlyList<BFnClause> Clauses { get; }\n    public BFnClauses(IEnumerable<BFnClause> clauses) => Clauses = clauses.ToList();\n}\n\npublic sealed class BRecord : Dictionary<string, object?> { }\n''',
        1)

    seed_text = seed_text.replace(
        '''        "fn" => value is BFn,\n''',
        '''        "fn" => value is BFn or BFnClauses,\n''',
        1)

    old_call = '''    public static BFn MakeFunction(int id, BEnv closure) => new(FunctionRegistry.Get(id), closure);\n\n    public static void RequireArgs(object?[] args, int count)\n    {\n        if (args.Length != count) throw new Exception($"Function expected {count} argument(s), got {args.Length}");\n    }\n\n    public static object? Call(object? callable, object? self, object?[] args) =>\n        callable is BFn fn ? fn.Code(fn.Closure, self, args) : throw new Exception("Value is not callable");\n'''
    new_call = '''    public static BFn MakeFunction(int id, BEnv closure) => new(FunctionRegistry.Get(id), closure);\n\n    public static BFnClauses MakeFunctionClauses(object?[] functions, string[][] parameterTypes)\n    {\n        if (functions.Length != parameterTypes.Length)\n            throw new Exception("Function clause metadata is inconsistent");\n\n        var clauses = new List<BFnClause>();\n        for (var i = 0; i < functions.Length; i++)\n        {\n            if (functions[i] is not BFn function)\n                throw new Exception("Function clause value is not a function");\n            clauses.Add(new BFnClause(function, parameterTypes[i]));\n        }\n        return new BFnClauses(clauses);\n    }\n\n    public static void RequireArgs(object?[] args, int count)\n    {\n        if (args.Length != count) throw new Exception($"Function expected {count} argument(s), got {args.Length}");\n    }\n\n    private static bool TypeMatches(BEnv env, string type, object? value)\n    {\n        var alternatives = type.Split('|', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);\n        foreach (var alternative in alternatives)\n        {\n            if (BuiltinTypeMatches(alternative, value)) return true;\n            if (IsBuiltinTypeName(alternative)) continue;\n\n            object? typeValue;\n            try { typeValue = env.Get(alternative); }\n            catch { continue; }\n\n            if (typeValue is BType beaconType && value is BRecord record)\n            {\n                try { _ = beaconType.Create(env, record); return true; }\n                catch { }\n            }\n        }\n        return false;\n    }\n\n    public static object? Call(object? callable, object? self, object?[] args)\n    {\n        if (callable is BFn fn) return fn.Code(fn.Closure, self, args);\n\n        if (callable is BFnClauses functionClauses)\n        {\n            foreach (var clause in functionClauses.Clauses)\n            {\n                if (clause.ParameterTypes.Length != args.Length) continue;\n\n                var matches = true;\n                for (var i = 0; i < args.Length; i++)\n                {\n                    if (!TypeMatches(clause.Function.Closure, clause.ParameterTypes[i], args[i]))\n                    {\n                        matches = false;\n                        break;\n                    }\n                }\n\n                if (matches) return clause.Function.Code(clause.Function.Closure, self, args);\n            }\n\n            var signature = string.Join(", ", args.Select(Kind));\n            throw new Exception($"No matching function clause for ({signature})");\n        }\n\n        throw new Exception("Value is not callable");\n    }\n'''
    if old_call not in seed_text:
        raise SystemExit('Seed MakeFunction/Call block not found')
    seed_text = seed_text.replace(old_call, new_call, 1)

    seed_text = seed_text.replace(
        '''        BFn => "fn",\n        BType => "type",\n''',
        '''        BFn => "fn",\n        BFnClauses => "fn",\n        BType => "type",\n''',
        1)

    method_info = '''    private static readonly MethodInfo MakeFunctionMethod = Method(nameof(Runtime.MakeFunction), typeof(int), typeof(BEnv));\n'''
    if method_info not in seed_text:
        raise SystemExit('Seed MakeFunction MethodInfo not found')
    seed_text = seed_text.replace(
        method_info,
        method_info + '    private static readonly MethodInfo MakeFunctionClausesMethod = Method(nameof(Runtime.MakeFunctionClauses), typeof(object[]), typeof(string[][]));\n',
        1)

    fn_case = '''            case "fn":\n                EmitFunction(instruction, ctx);\n                return;\n'''
    if fn_case not in seed_text:
        raise SystemExit('Seed fn plan case not found')
    seed_text = seed_text.replace(
        fn_case,
        '''            case "fn.clauses":\n                EmitFunctionClauses(instruction, ctx);\n                return;\n''' + fn_case,
        1)

    emit_fn_marker = '''    private static void EmitFunction(BRecord instruction, PlanContext parent)\n    {\n'''
    if emit_fn_marker not in seed_text:
        raise SystemExit('Seed EmitFunction marker not found')
    emit_clauses = '''    private static void EmitFunctionClauses(BRecord instruction, PlanContext ctx)\n    {\n        var clauses = ListField(instruction, "clauses");\n        var il = ctx.IL;\n\n        il.Emit(OpCodes.Ldc_I4, clauses.Count);\n        il.Emit(OpCodes.Newarr, typeof(object));\n        for (var i = 0; i < clauses.Count; i++)\n        {\n            var clause = clauses[i] as BRecord ?? throw new Exception("Function clause plan must be a Record");\n            il.Emit(OpCodes.Dup);\n            il.Emit(OpCodes.Ldc_I4, i);\n            EmitPlan(ListField(clause, "value"), ctx);\n            il.Emit(OpCodes.Stelem_Ref);\n        }\n\n        il.Emit(OpCodes.Ldc_I4, clauses.Count);\n        il.Emit(OpCodes.Newarr, typeof(string[]));\n        for (var i = 0; i < clauses.Count; i++)\n        {\n            var clause = (BRecord)clauses[i]!;\n            var types = ListField(clause, "types")\n                .Select(x => x as string ?? throw new Exception("Function clause type must be a String"))\n                .ToArray();\n            il.Emit(OpCodes.Dup);\n            il.Emit(OpCodes.Ldc_I4, i);\n            EmitStringArray(types, il);\n            il.Emit(OpCodes.Stelem_Ref);\n        }\n\n        il.Emit(OpCodes.Call, MakeFunctionClausesMethod);\n    }\n\n'''
    seed_text = seed_text.replace(emit_fn_marker, emit_clauses + emit_fn_marker, 1)
    seed.write_text(seed_text)
