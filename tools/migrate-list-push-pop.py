from pathlib import Path

ROOT = Path('.')
SEED = ROOT / 'tools/seed-refresh/Beacon.Compiler/Program.cs'


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'Expected exactly one {label} match, found {count}')
    return text.replace(old, new, 1)


# Migrate Beacon code to the renamed List mutation primitive.
for root_name in ('compiler', 'examples', 'std'):
    root = ROOT / root_name
    if not root.exists():
        continue
    for path in root.rglob('*.beacon'):
        text = path.read_text()
        if '.append(' in text:
            path.write_text(text.replace('.append(', '.push('))


# Keep the bootstrap primitive example explicit about both stack operations.
bootstrap_example = ROOT / 'examples/bootstrap-primitives.beacon'
example_text = bootstrap_example.read_text()
old_example = '''values: list = ["a", "b"]\nvalues.push("c")\nmore: list = values.concat(["d", "e"])\n'''
new_example = '''values: list = ["a", "b"]\nvalues.push("c")\nprint(values.pop())\nvalues.push("c")\nmore: list = values.concat(["d", "e"])\n'''
example_text = replace_once(example_text, old_example, new_example, 'bootstrap List example')
bootstrap_example.write_text(example_text)


# Document the public List surface.
readme = ROOT / 'README.md'
readme_text = readme.read_text()
marker = '''List indexing uses `@`:\n\n```beacon\nvalues@0\nvalues@i\nvalues@(i + 1)\n```\n'''
replacement = marker + '''\nLists use stack-style mutation methods:\n\n```beacon\nvalues.push(42)   // append to the end\nlast = values.pop() // remove and return the final value\n```\n\n`pop()` fails on an empty List. The previous `append()` name is not retained as an alias.\n'''
readme_text = replace_once(readme_text, marker, replacement, 'README List methods')
readme.write_text(readme_text)


if not SEED.exists():
    raise SystemExit(f'Missing reconstructed seed source: {SEED}')

seed = SEED.read_text()
if '@ requires a List on the left' not in seed:
    raise SystemExit('Seed source is not the expected List-only baseline')
if 'RecordGet' not in seed or 'RecordSet' not in seed:
    raise SystemExit('Seed source is missing explicit Record get/set semantics')


# Reapply the function-clause runtime layer that was added after the List-only
# source snapshot. Unary minus, break/continue, and multiline expressions did
# not change Stage-0, so this recreates the current runtime baseline.
if 'BFnClauses' not in seed:
    seed = replace_once(
        seed,
        'public sealed class BRecord : Dictionary<string, object?> { }\n',
        '''public sealed record BFnClause(BFn Function, string[] ParameterTypes);\n\npublic sealed class BFnClauses\n{\n    public IReadOnlyList<BFnClause> Clauses { get; }\n    public BFnClauses(IEnumerable<BFnClause> clauses) => Clauses = clauses.ToList();\n}\n\npublic sealed class BRecord : Dictionary<string, object?> { }\n''',
        'BFnClauses type insertion')

    seed = replace_once(
        seed,
        '        "fn" => value is BFn,\n',
        '        "fn" => value is BFn or BFnClauses,\n',
        'fn type matching')

    old_call = '''    public static BFn MakeFunction(int id, BEnv closure) => new(FunctionRegistry.Get(id), closure);\n\n    public static void RequireArgs(object?[] args, int count)\n    {\n        if (args.Length != count) throw new Exception($"Function expected {count} argument(s), got {args.Length}");\n    }\n\n    public static object? Call(object? callable, object? self, object?[] args) =>\n        callable is BFn fn ? fn.Code(fn.Closure, self, args) : throw new Exception("Value is not callable");\n'''
    new_call = '''    public static BFn MakeFunction(int id, BEnv closure) => new(FunctionRegistry.Get(id), closure);\n\n    public static BFnClauses MakeFunctionClauses(object?[] functions, string[][] parameterTypes)\n    {\n        if (functions.Length != parameterTypes.Length)\n            throw new Exception("Function clause metadata is inconsistent");\n\n        var clauses = new List<BFnClause>();\n        for (var i = 0; i < functions.Length; i++)\n        {\n            if (functions[i] is not BFn function)\n                throw new Exception("Function clause value is not a function");\n            clauses.Add(new BFnClause(function, parameterTypes[i]));\n        }\n        return new BFnClauses(clauses);\n    }\n\n    public static void RequireArgs(object?[] args, int count)\n    {\n        if (args.Length != count) throw new Exception($"Function expected {count} argument(s), got {args.Length}");\n    }\n\n    private static bool TypeMatches(BEnv env, string type, object? value)\n    {\n        var alternatives = type.Split('|', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);\n        foreach (var alternative in alternatives)\n        {\n            if (BuiltinTypeMatches(alternative, value)) return true;\n            if (IsBuiltinTypeName(alternative)) continue;\n\n            object? typeValue;\n            try { typeValue = env.Get(alternative); }\n            catch { continue; }\n\n            if (typeValue is BType beaconType && value is BRecord record)\n            {\n                try { _ = beaconType.Create(env, record); return true; }\n                catch { }\n            }\n        }\n        return false;\n    }\n\n    public static object? Call(object? callable, object? self, object?[] args)\n    {\n        if (callable is BFn fn) return fn.Code(fn.Closure, self, args);\n\n        if (callable is BFnClauses functionClauses)\n        {\n            foreach (var clause in functionClauses.Clauses)\n            {\n                if (clause.ParameterTypes.Length != args.Length) continue;\n\n                var matches = true;\n                for (var i = 0; i < args.Length; i++)\n                {\n                    if (!TypeMatches(clause.Function.Closure, clause.ParameterTypes[i], args[i]))\n                    {\n                        matches = false;\n                        break;\n                    }\n                }\n\n                if (matches) return clause.Function.Code(clause.Function.Closure, self, args);\n            }\n\n            var signature = string.Join(", ", args.Select(Kind));\n            throw new Exception($"No matching function clause for ({signature})");\n        }\n\n        throw new Exception("Value is not callable");\n    }\n'''
    seed = replace_once(seed, old_call, new_call, 'function clause Call block')

    seed = replace_once(
        seed,
        '        BFn => "fn",\n        BType => "type",\n',
        '        BFn => "fn",\n        BFnClauses => "fn",\n        BType => "type",\n',
        'function clause Kind')

    method_info = '    private static readonly MethodInfo MakeFunctionMethod = Method(nameof(Runtime.MakeFunction), typeof(int), typeof(BEnv));\n'
    seed = replace_once(
        seed,
        method_info,
        method_info + '    private static readonly MethodInfo MakeFunctionClausesMethod = Method(nameof(Runtime.MakeFunctionClauses), typeof(object[]), typeof(string[][]));\n',
        'MakeFunctionClauses MethodInfo')

    fn_case = '''            case "fn":\n                EmitFunction(instruction, ctx);\n                return;\n'''
    seed = replace_once(
        seed,
        fn_case,
        '''            case "fn.clauses":\n                EmitFunctionClauses(instruction, ctx);\n                return;\n''' + fn_case,
        'fn.clauses plan case')

    emit_fn_marker = '''    private static void EmitFunction(BRecord instruction, PlanContext parent)\n    {\n'''
    emit_clauses = '''    private static void EmitFunctionClauses(BRecord instruction, PlanContext ctx)\n    {\n        var clauses = ListField(instruction, "clauses");\n        var il = ctx.IL;\n\n        il.Emit(OpCodes.Ldc_I4, clauses.Count);\n        il.Emit(OpCodes.Newarr, typeof(object));\n        for (var i = 0; i < clauses.Count; i++)\n        {\n            var clause = clauses[i] as BRecord ?? throw new Exception("Function clause plan must be a Record");\n            il.Emit(OpCodes.Dup);\n            il.Emit(OpCodes.Ldc_I4, i);\n            EmitPlan(ListField(clause, "value"), ctx);\n            il.Emit(OpCodes.Stelem_Ref);\n        }\n\n        il.Emit(OpCodes.Ldc_I4, clauses.Count);\n        il.Emit(OpCodes.Newarr, typeof(string[]));\n        for (var i = 0; i < clauses.Count; i++)\n        {\n            var clause = (BRecord)clauses[i]!;\n            var types = ListField(clause, "types")\n                .Select(x => x as string ?? throw new Exception("Function clause type must be a String"))\n                .ToArray();\n            il.Emit(OpCodes.Dup);\n            il.Emit(OpCodes.Ldc_I4, i);\n            EmitStringArray(types, il);\n            il.Emit(OpCodes.Stelem_Ref);\n        }\n\n        il.Emit(OpCodes.Call, MakeFunctionClausesMethod);\n    }\n\n'''
    seed = replace_once(seed, emit_fn_marker, emit_clauses + emit_fn_marker, 'EmitFunctionClauses')


# Rename the existing mutator and add a true stack pop primitive.
old_list_methods = '''    private static readonly BFn ListAppend = NativeMethod(1, (self, args) =>\n    {\n        if (self is not List<object?> list) throw new Exception("append() requires a List receiver");\n        list.Add(args[0]);\n        return list;\n    });\n\n    private static readonly BFn ListConcat = NativeMethod(1, (self, args) =>\n'''
new_list_methods = '''    private static readonly BFn ListPush = NativeMethod(1, (self, args) =>\n    {\n        if (self is not List<object?> list) throw new Exception("push() requires a List receiver");\n        list.Add(args[0]);\n        return list;\n    });\n\n    private static readonly BFn ListPop = NativeMethod(0, (self, _) =>\n    {\n        if (self is not List<object?> list) throw new Exception("pop() requires a List receiver");\n        if (list.Count == 0) throw new Exception("pop() cannot remove from an empty List");\n        var index = list.Count - 1;\n        var value = list[index];\n        list.RemoveAt(index);\n        return value;\n    });\n\n    private static readonly BFn ListConcat = NativeMethod(1, (self, args) =>\n'''
seed = replace_once(seed, old_list_methods, new_list_methods, 'List push/pop methods')

old_dispatch = '''                "length" => ListLength,\n                "append" => ListAppend,\n                "concat" => ListConcat,\n'''
new_dispatch = '''                "length" => ListLength,\n                "push" => ListPush,\n                "pop" => ListPop,\n                "concat" => ListConcat,\n'''
seed = replace_once(seed, old_dispatch, new_dispatch, 'List method dispatch')

SEED.write_text(seed)
