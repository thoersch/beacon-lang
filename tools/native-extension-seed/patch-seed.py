from pathlib import Path

path = Path("tools/seed-refresh/Beacon.Compiler/Program.cs")
source = path.read_text()

def swap(old, new, name):
    global source
    if source.count(old) != 1:
        raise SystemExit(f"Expected one {name}; found {source.count(old)}")
    source = source.replace(old, new, 1)

swap(
'''    private static readonly MethodInfo HostInspectMethod = Method(nameof(Runtime.HostInspect), typeof(object), typeof(object));
''',
'''    private static readonly MethodInfo HostInspectMethod = Method(nameof(Runtime.HostInspect), typeof(object), typeof(object));
    private static readonly MethodInfo HostNativeMethod = Method(nameof(Runtime.HostNative), typeof(object), typeof(object));
''',
"extension method registration")

swap(
'''        "Runtime.HostInspect" => HostInspectMethod,
''',
'''        "Runtime.HostInspect" => HostInspectMethod,
        "Runtime.HostNative" => HostNativeMethod,
''',
"extension symbolic call")

swap(
'''            "controls" => BeaconApplyControls(payload),
''',
'''            "controls" => BeaconApplyControls(payload),
            // General native HWND query. Keep raw handle internal to std library code.
            "nativeHandle" => BeaconWindowState(payload).Handle.ToInt64().ToString("X"),
''',
"platform-neutral native window handle export")

path.write_text(source)
print("Native module ABI and generic window handle access installed.")
