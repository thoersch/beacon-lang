from pathlib import Path

path = Path("tools/seed-refresh/Beacon.Compiler/Program.cs")
source = path.read_text()

def section(start, end, replacement, label):
    global source
    a = source.find(start)
    b = source.find(end, a + len(start))
    if a < 0 or b < 0:
        raise SystemExit(f"Cannot find {label} boundaries")
    if source.find(start, a + 1) != -1:
        raise SystemExit(f"Multiple {label} starts")
    source = source[:a] + replacement + "\n\n" + source[b:]

def swap(old, new, label, count=1):
    global source
    n = source.count(old)
    if n != count:
        raise SystemExit(f"Expected {count} {label}, found {n}")
    source = source.replace(old, new, count)

section(
    "public sealed class BEnv\n",
    "public delegate object? BCallable",
"""public sealed class BEnv
{
    private readonly Dictionary<string, object?> _values = new();
    private readonly Dictionary<string, string> _declaredTypes = new();
    public BEnv? Parent { get; }

    public BEnv() { Runtime.CaptureInspectedRoot(this); }
    public BEnv(BEnv? parent) => Parent = parent;

    public Dictionary<string, object?> InspectEntries()
    {
        lock (Runtime.InspectGate)
            return new Dictionary<string, object?>(_values);
    }

    public void Define(string name, object? value, string? type = null)
    {
        lock (Runtime.InspectGate)
        {
            _values[name] = value;
            if (type is not null) _declaredTypes[name] = type;
        }
    }

    public object? Get(string name)
    {
        lock (Runtime.InspectGate)
        {
            if (_values.TryGetValue(name, out var value)) return value;
            if (Parent is not null) return Parent.Get(name);
            throw new Exception($"Unknown symbol '{name}'");
        }
    }

    public object? Set(string name, object? value)
    {
        lock (Runtime.InspectGate)
        {
            if (_values.ContainsKey(name))
            {
                if (_declaredTypes.TryGetValue(name, out var type))
                    value = Runtime.CheckType(this, type, value);
                _values[name] = value;
                return value;
            }
            if (Parent is not null) return Parent.Set(name, value);
            throw new Exception($"Unknown symbol '{name}'");
        }
    }
}""",
    "environment type tracking")

section(
    "public sealed class BRecord : Dictionary<string, object?>",
    "static class FunctionRegistry",
"""public sealed class BRecord : Dictionary<string, object?>
{
    // Named type identity is metadata; Records remain Beacon's named structure.
    public BType? DeclaredType { get; set; }
    public BEnv? TypeEnvironment { get; set; }
}

public sealed class BList : List<object?>
{
    public string ElementType { get; }
    public BEnv TypeEnvironment { get; }

    public BList(BEnv environment, string elementType, IEnumerable<object?> values)
        : base(values)
    {
        TypeEnvironment = environment;
        ElementType = elementType;
    }
}

// Runtime representation of a Beacon symbol when compiler Core is exposed to Beacon.
public sealed record BSymbol(string Name);

public sealed class BType
{
    public string Name { get; }
    public Dictionary<string, string> Fields { get; }
    public BRecord Methods { get; }

    public BType(string name, Dictionary<string, string> fields, BRecord methods)
    {
        Name = name;
        Fields = fields;
        Methods = methods;
    }

    public BRecord Create(BEnv env, BRecord values)
    {
        if (values.DeclaredType is not null)
        {
            if (!ReferenceEquals(values.DeclaredType, this))
                throw new Exception($"Expected {Name}, got {values.DeclaredType.Name}");
            return values;
        }

        foreach (var key in values.Keys)
            if (!Fields.ContainsKey(key))
                throw new Exception($"Unknown field '{key}' in {Name}");

        var result = new BRecord { DeclaredType = this, TypeEnvironment = env };
        foreach (var field in Fields)
        {
            if (!values.TryGetValue(field.Key, out var value))
                throw new Exception($"Missing {Name}.{field.Key}");
            try
            {
                result[field.Key] = Runtime.CheckType(env, field.Value, value);
            }
            catch (Exception ex)
            {
                throw new Exception($"Invalid {Name}.{field.Key}: {ex.Message}");
            }
        }
        foreach (var method in Methods) result[method.Key] = method.Value;
        return result;
    }
}""",
    "typed Record and List representation")

section(
    "    private static readonly BFn ListPush = NativeMethod",
    "    private static readonly BFn ListPop = NativeMethod",
"""    private static readonly BFn ListPush = NativeMethod(1, (self, args) =>
    {
        if (self is not List<object?> list) throw new Exception("push() requires a List receiver");
        var value = CheckListItem(list, args[0]);
        lock (InspectGate) list.Add(value);
        return list;
    });""",
    "list push")

section(
    "    private static readonly BFn ListFilter = NativeMethod",
    "    private static readonly BFn ListHead = NativeMethod",
"""    private static readonly BFn ListFilter = NativeMethod(1, (self, args) =>
    {
        if (self is not List<object?> list) throw new Exception("filter() requires a List receiver");
        var result = new List<object?>();
        foreach (var value in list)
        {
            var predicate = Call(args[0], null, new object?[] { value });
            if (predicate is not bool include)
                throw new Exception("filter() predicate must return a Boolean");
            if (include) result.Add(value);
        }
        return PreserveListType(list, result);
    });""",
    "typed filter")

section(
    "    private static readonly BFn ListTail = NativeMethod",
    "    private static readonly BFn NumberFloor = NativeMethod",
"""    private static readonly BFn ListTail = NativeMethod(0, (self, _) =>
    {
        if (self is not List<object?> list) throw new Exception("tail() requires a List receiver");
        if (list.Count == 0) throw new Exception("tail() cannot read from an empty List");
        return PreserveListType(list, list.Skip(1).ToList());
    });

    private static readonly BFn ListConcat = NativeMethod(1, (self, args) =>
    {
        if (self is not List<object?> left || args[0] is not List<object?> right)
            throw new Exception("concat() requires Lists");
        if (left is BList typed)
        {
            var checkedRight = (List<object?>)CheckType(typed.TypeEnvironment, $"list<{typed.ElementType}>", right)!;
            return PreserveListType(left, left.Concat(checkedRight).ToList());
        }
        return left.Concat(right).ToList();
    });""",
    "typed tail and concat")

section(
    "    private static readonly BFn RecordSet = NativeMethod",
    "    private static BFn NativeMethod",
"""    private static readonly BFn RecordSet = NativeMethod(2, (self, args) =>
    {
        if (self is not BRecord record || args[0] is not string key)
            throw new Exception("set() requires a Record receiver, String key, and value");
        return SetMember(record, key, args[1]);
    });""",
    "named Record mutation")

swap("        env.Define(name, checkedValue);\n","        env.Define(name, checkedValue, type);\n","store type of declared binding")

section(
    "    public static object? CheckType(BEnv env, string type, object? value)\n",
    "    public static BFn MakeFunction(",
"""    // A union's top-level pipes are distinct from pipes inside list<T|U>.
    private static List<string> SplitTypeUnion(string annotation)
    {
        var alternatives = new List<string>();
        var depth = 0;
        var start = 0;
        for (var i = 0; i < annotation.Length; i++)
        {
            switch (annotation[i])
            {
                case '<': depth++; break;
                case '>': depth--; break;
                case '|' when depth == 0:
                    alternatives.Add(annotation[start..i].Trim());
                    start = i + 1;
                    break;
            }
            if (depth < 0) throw new Exception($"Invalid type annotation '{annotation}'");
        }
        if (depth != 0) throw new Exception($"Invalid type annotation '{annotation}'");
        alternatives.Add(annotation[start..].Trim());
        if (alternatives.Any(x => x.Length == 0)) throw new Exception("Empty type alternative");
        return alternatives;
    }

    private static bool IsConstrainedList(string type) =>
        type.StartsWith("list<", StringComparison.Ordinal) &&
        type.EndsWith(">", StringComparison.Ordinal);

    // Empty Lists still require valid element type annotations.
    private static void VerifyElementTypes(BEnv env, string annotation)
    {
        foreach (var alternative in SplitTypeUnion(annotation))
        {
            if (alternative == "any")
                throw new Exception("Beacon has no 'any' type");
            if (IsConstrainedList(alternative))
            {
                VerifyElementTypes(env, alternative.Substring(5, alternative.Length - 6));
                continue;
            }
            if (IsBuiltinTypeName(alternative)) continue;
            object? definition;
            try { definition = env.Get(alternative); }
            catch { throw new Exception($"Unknown type '{alternative}' in List element constraint"); }
            if (definition is not BType)
                throw new Exception($"'{alternative}' is not a Beacon type");
        }
    }

    private static object? CheckListItem(List<object?> list, object? value) =>
        list is BList typed
            ? CheckType(typed.TypeEnvironment, typed.ElementType, value)
            : value;

    private static List<object?> PreserveListType(List<object?> original, IEnumerable<object?> values) =>
        original is BList typed
            ? new BList(typed.TypeEnvironment, typed.ElementType, values)
            : values.ToList();

    private static object? CheckOneType(BEnv env, string type, object? value)
    {
        if (IsConstrainedList(type))
        {
            if (value is not List<object?> list)
                throw new Exception($"Expected {type}, got {Kind(value)}");
            var elementType = type.Substring(5, type.Length - 6);
            VerifyElementTypes(env, elementType);
            if (list is BList existing)
            {
                if (existing.ElementType != elementType)
                    throw new Exception($"Cannot assign list<{existing.ElementType}> to {type}: mutable Lists are invariant");
                return existing;
            }
            var checkedValues = new List<object?>();
            for (var i = 0; i < list.Count; i++)
            {
                try { checkedValues.Add(CheckType(env, elementType, list[i])); }
                catch (Exception ex)
                {
                    throw new Exception($"Invalid {type} element @{i}: {ex.Message}");
                }
            }
            return new BList(env, elementType, checkedValues);
        }

        if (BuiltinTypeMatches(type, value)) return value;
        if (IsBuiltinTypeName(type))
            throw new Exception($"Expected {type}, got {Kind(value)}");

        object? typeValue;
        try { typeValue = env.Get(type); }
        catch { throw new Exception($"Unknown type '{type}'"); }
        if (typeValue is not BType namedType)
            throw new Exception($"'{type}' is not a Beacon type");
        if (value is not BRecord record)
            throw new Exception($"Expected {type}, got {Kind(value)}");
        return namedType.Create(env, record);
    }

    public static object? CheckType(BEnv env, string type, object? value)
    {
        if (type == "any")
            throw new Exception("Beacon has no 'any' type; declarations must be explicitly typed");

        var alternatives = SplitTypeUnion(type);
        object? result = null;
        var matches = 0;
        string? lastError = null;
        foreach (var alternative in alternatives)
        {
            try
            {
                var checkedValue = CheckOneType(env, alternative, value);
                if (matches == 0) result = checkedValue;
                matches++;
            }
            catch (Exception ex) { lastError = ex.Message; }
        }

        if (matches == 0)
        {
            if (alternatives.Count == 1 && lastError is not null)
                throw new Exception(lastError);
            throw new Exception($"Expected {type}, got {Kind(value)}");
        }
        if (matches > 1 && value is BRecord { DeclaredType: null })
            throw new Exception($"Ambiguous Record for {type}; use an explicit constructor such as item {{ ... }}");
        return result;
    }

    private static bool IsBuiltinTypeName(string type) => type is
        "number" or "string" or "boolean" or "list" or "record" or
        "symbol" or "atom" or "null" or "fn" or "type";

    private static bool BuiltinTypeMatches(string type, object? value) => type switch
    {
        "number" => value is double,
        "string" => value is string,
        "boolean" => value is bool,
        "list" => value is List<object?>,
        "record" => value is BRecord,
        "symbol" => value is BSymbol,
        "atom" => value is null or BSymbol or double or string or bool,
        "null" => value is null,
        "fn" => value is BFn or BFnClauses,
        "type" => value is BType,
        _ => false
    };""",
    "nested union/type enforcement")

section(
    "    private static bool TypeMatches(BEnv env, string type, object? value)\n",
    "    public static object? Call(",
"""    private static bool TypeMatches(BEnv env, string type, object? value)
    {
        try { _ = CheckType(env, type, value); return true; }
        catch { return false; }
    }""",
    "typed function clause compatibility")

section(
    "    public static object? SetMember(object? target, string member, object? value)\n",
    "    public static object? Index(",
"""    public static object? SetMember(object? target, string member, object? value)
    {
        if (target is not BRecord record) throw new Exception($"Cannot assign .{member} on non-Record");
        if (record.DeclaredType is BType descriptor)
        {
            if (!descriptor.Fields.TryGetValue(member, out var expected))
                throw new Exception($"Unknown field '{member}' in {descriptor.Name}");
            value = CheckType(record.TypeEnvironment!, expected, value);
        }
        lock (InspectGate) record[member] = value;
        return value;
    }""",
    "typed Record field mutation")

section(
    "    public static object? SetIndex(object? target, object? index, object? value)\n",
    "    private static int WholeIndex(",
"""    public static object? SetIndex(object? target, object? index, object? value)
    {
        if (target is List<object?> list)
        {
            var i = WholeIndex(index, "List index");
            if (i < 0 || i >= list.Count) throw new Exception($"List index {i} is out of range");
            value = CheckListItem(list, value);
            lock (InspectGate) list[i] = value;
            return value;
        }
        throw new Exception("@ assignment requires a List on the left");
    }""",
    "typed List index assignment")

section(
    "    public static object? AddAssignMember(object? target, string member, object? value)\n",
    "    public static object? Add(",
"""    public static object? AddAssignMember(object? target, string member, object? value)
    {
        if (target is not BRecord record) throw new Exception($"Cannot assign .{member} on non-Record");
        var result = Add(Get(record, member), value);
        return SetMember(record, member, result);
    }""",
    "typed Record arithmetic assignment")

swap(
"""    private static readonly MethodInfo DeclareMethod = Method(nameof(Runtime.Declare), typeof(BEnv), typeof(string), typeof(string), typeof(object));
""",
"""    private static readonly MethodInfo DeclareMethod = Method(nameof(Runtime.Declare), typeof(BEnv), typeof(string), typeof(string), typeof(object));
    private static readonly MethodInfo CheckTypeMethod = Method(nameof(Runtime.CheckType), typeof(BEnv), typeof(string), typeof(object));
""",
"Stage-1 CheckType method info")
swap(
"""        "Runtime.Declare" => DeclareMethod,
""",
"""        "Runtime.Declare" => DeclareMethod,
        "Runtime.CheckType" => CheckTypeMethod,
""",
"Stage-1 CheckType method dispatch")

path.write_text(source)
print("Patched typed Lists and named Record construction into Stage-0 runtime.")
