from pathlib import Path

path = Path("tools/seed-refresh/Beacon.Compiler/Program.cs")
text = path.read_text()

def replace_once(old: str, new: str, label: str):
    global text
    if text.count(old) != 1:
        raise SystemExit(f"Expected one {label}, got {text.count(old)}")
    text = text.replace(old, new, 1)

replace_once("public static class Runtime\n", "public static partial class Runtime\n", "Runtime partial class")

replace_once(
'''    public BEnv() { }
    public BEnv(BEnv? parent) => Parent = parent;

    public void Define(string name, object? value) => _values[name] = value;

    public object? Get(string name)
    {
        if (_values.TryGetValue(name, out var value)) return value;
        if (Parent is not null) return Parent.Get(name);
        throw new Exception($"Unknown symbol '{name}'");
    }

    public object? Set(string name, object? value)
    {
        if (_values.ContainsKey(name)) { _values[name] = value; return value; }
        if (Parent is not null) return Parent.Set(name, value);
        throw new Exception($"Unknown symbol '{name}'");
    }
''',
'''    public BEnv() { Runtime.CaptureInspectedRoot(this); }
    public BEnv(BEnv? parent) => Parent = parent;

    public Dictionary<string, object?> InspectEntries()
    {
        lock (Runtime.InspectGate)
            return new Dictionary<string, object?>(_values);
    }

    public void Define(string name, object? value)
    {
        lock (Runtime.InspectGate) _values[name] = value;
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
            if (_values.ContainsKey(name)) { _values[name] = value; return value; }
            if (Parent is not null) return Parent.Set(name, value);
            throw new Exception($"Unknown symbol '{name}'");
        }
    }
''', "synchronized root environment snapshot and capture")

replace_once(
'''        list.Add(args[0]);
        return list;
''',
'''        lock (InspectGate) list.Add(args[0]);
        return list;
''', "synchronized list push")
replace_once(
'''        var index = list.Count - 1;
        var value = list[index];
        list.RemoveAt(index);
        return value;
''',
'''        lock (InspectGate)
        {
            var index = list.Count - 1;
            var value = list[index];
            list.RemoveAt(index);
            return value;
        }
''', "synchronized list pop")
replace_once(
'''        record[key] = args[1];
        return args[1];
''',
'''        lock (InspectGate) record[key] = args[1];
        return args[1];
''', "synchronized record set")

replace_once(
'''        record[member] = value;
        return value;
''',
'''        lock (InspectGate) record[member] = value;
        return value;
''', "synchronized record assignment")
replace_once(
'''            list[i] = value;
            return value;
''',
'''            lock (InspectGate) list[i] = value;
            return value;
''', "synchronized list assignment")
replace_once(
'''        record[member] = result;
        return result;
''',
'''        lock (InspectGate) record[member] = result;
        return result;
''', "synchronized record add assignment")

replace_once(
'''    private static readonly MethodInfo HostWindowMethod = Method(nameof(Runtime.HostWindow), typeof(object), typeof(object));
''',
'''    private static readonly MethodInfo HostWindowMethod = Method(nameof(Runtime.HostWindow), typeof(object), typeof(object));
    private static readonly MethodInfo HostInspectMethod = Method(nameof(Runtime.HostInspect), typeof(object), typeof(object));
''', "inspector assembler method info")
replace_once(
'''        "Runtime.HostWindow" => HostWindowMethod,
''',
'''        "Runtime.HostWindow" => HostWindowMethod,
        "Runtime.HostInspect" => HostInspectMethod,
''', "inspector assembler symbolic call map")

replace_once(
'''                if (stage1RunIndex >= 0)
                {
                    new PlanAssembler().Compile(plan).Run();
                    return 0;
                }
''',
'''                if (stage1RunIndex >= 0)
                {
                    var executable = new PlanAssembler().Compile(plan);
                    var inspect = args.Contains("--inspect");
                    if (inspect) Runtime.BeginInspection(targetPath);
                    try { executable.Run(); }
                    finally { if (inspect) Runtime.EndInspection(); }
                    return 0;
                }
''', "opt-in inspected app lifecycle")

path.write_text(text)
