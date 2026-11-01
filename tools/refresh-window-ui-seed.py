from pathlib import Path
import re
import sys


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one {label} match, found {count}")
    return text.replace(old, new, 1)


def patch_emitter() -> None:
    path = Path("compiler/emitter.beacon")
    text = path.read_text()
    anchor = '''    if not handled and kind(callee) == "symbol" and callee.name == "hostCharacter" then
        result = args@0
        result.push({ op: "call", arg: "Runtime.HostCharacter" })
        handled = true
    end,
'''
    addition = anchor + '''    if not handled and kind(callee) == "symbol" and callee.name == "hostWindow" then
        if args.length() != 2 then
            fail("hostWindow() expects two arguments")
        end
        result = args@0
        result = result.concat(args@1)
        result.push({ op: "call", arg: "Runtime.HostWindow" })
        handled = true
    end,
'''
    path.write_text(replace_once(text, anchor, addition, "hostCharacter emitter block"))


def patch_else_if_parser(text: str) -> str:
    pattern = re.compile(
        r'''    private Core ParseIf\(\)\n    \{\n.*?\n    \}\n\n    private Core ParseFor\(\)''',
        re.S,
    )
    if len(list(pattern.finditer(text))) != 1:
        raise SystemExit("Expected exactly one ParseIf block")
    replacement = '''    private Core ParseIf()\n    {\n        ConsumeIdentifier("if", "Expected 'if'");\n        var conditions = new List<Core>();\n        var bodies = new List<Core>();\n        Core elseBody = new ListCore(new List<Core> { Atom.Symbol("do") });\n\n        ParseIfClause(conditions, bodies);\n\n        var chaining = true;\n        while (chaining && MatchIdentifier("else"))\n        {\n            if (MatchIdentifier("if"))\n            {\n                ParseIfClause(conditions, bodies);\n            }\n            else\n            {\n                RequireNewLine("Expected newline after 'else'");\n                elseBody = ParseStatementsUntil("end");\n                chaining = false;\n            }\n        }\n\n        ConsumeIdentifier("end", "Expected 'end' to close if");\n\n        Core result = CoreForms.Form("if", conditions[^1], bodies[^1], elseBody);\n        for (var i = conditions.Count - 2; i >= 0; i--)\n        {\n            result = CoreForms.Form(\n                "if",\n                conditions[i],\n                bodies[i],\n                new ListCore(new List<Core> { Atom.Symbol("do"), result }));\n        }\n        return result;\n    }\n\n    private void ParseIfClause(List<Core> conditions, List<Core> bodies)\n    {\n        var condition = ParseExpression();\n        ConsumeIdentifier("then", "Expected 'then' after if condition");\n        RequireNewLine("Expected newline after 'then'");\n        conditions.Add(condition);\n        bodies.Add(ParseStatementsUntil("else", "end"));\n    }\n\n    private Core ParseFor()'''
    return pattern.sub(replacement, text, count=1)


WINDOW_RUNTIME = r'''    private sealed class BeaconNativeWindow
    {
        public int Id { get; init; }
        public IntPtr Handle { get; init; }
        public System.Collections.Generic.Queue<BRecord> Events { get; } = new();
        public System.Collections.Generic.List<IntPtr> Controls { get; } = new();
        public System.Collections.Generic.Dictionary<int, string> Actions { get; } = new();
        public System.Collections.Generic.Dictionary<int, string> Kinds { get; } = new();
    }

    [System.Runtime.InteropServices.StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential, CharSet = System.Runtime.InteropServices.CharSet.Unicode)]
    private struct BeaconWindowClass
    {
        public uint style;
        public IntPtr lpfnWndProc;
        public int cbClsExtra;
        public int cbWndExtra;
        public IntPtr hInstance;
        public IntPtr hIcon;
        public IntPtr hCursor;
        public IntPtr hbrBackground;
        [System.Runtime.InteropServices.MarshalAs(System.Runtime.InteropServices.UnmanagedType.LPWStr)] public string? lpszMenuName;
        [System.Runtime.InteropServices.MarshalAs(System.Runtime.InteropServices.UnmanagedType.LPWStr)] public string lpszClassName;
    }

    [System.Runtime.InteropServices.StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential)]
    private struct BeaconPoint
    {
        public int x;
        public int y;
    }

    [System.Runtime.InteropServices.StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential)]
    private struct BeaconMessage
    {
        public IntPtr hwnd;
        public uint message;
        public IntPtr wParam;
        public IntPtr lParam;
        public uint time;
        public BeaconPoint pt;
        public uint lPrivate;
    }

    private delegate IntPtr BeaconWindowProcDelegate(IntPtr hwnd, uint message, IntPtr wParam, IntPtr lParam);

    private static readonly System.Collections.Generic.Dictionary<int, BeaconNativeWindow> BeaconWindows = new();
    private static readonly System.Collections.Generic.Dictionary<IntPtr, BeaconNativeWindow> BeaconWindowsByHandle = new();
    private static readonly BeaconWindowProcDelegate BeaconWindowProcedure = BeaconNativeWindowProc;
    private static readonly string BeaconWindowClassName = "Beacon.Native.Window";
    private static int BeaconNextWindowId = 1;
    private static int BeaconNextControlId = 1000;
    private static bool BeaconWindowClassRegistered;

    private const uint BeaconWmClose = 0x0010;
    private const uint BeaconWmDestroy = 0x0002;
    private const uint BeaconWmSize = 0x0005;
    private const uint BeaconWmCommand = 0x0111;
    private const uint BeaconWmKeyDown = 0x0100;
    private const uint BeaconWmKeyUp = 0x0101;
    private const uint BeaconWmMouseMove = 0x0200;
    private const uint BeaconWmLeftDown = 0x0201;
    private const uint BeaconWmLeftUp = 0x0202;
    private const uint BeaconWmSetFont = 0x0030;
    private const int BeaconEnChange = 0x0300;

    [System.Runtime.InteropServices.DllImport("user32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode, SetLastError = true)]
    private static extern ushort RegisterClassW(ref BeaconWindowClass windowClass);

    [System.Runtime.InteropServices.DllImport("user32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr CreateWindowExW(uint extendedStyle, string className, string? title, uint style, int x, int y, int width, int height, IntPtr parent, IntPtr menu, IntPtr instance, IntPtr parameter);

    [System.Runtime.InteropServices.DllImport("user32.dll", SetLastError = true)]
    private static extern bool DestroyWindow(IntPtr hwnd);

    [System.Runtime.InteropServices.DllImport("user32.dll")]
    private static extern bool ShowWindow(IntPtr hwnd, int command);

    [System.Runtime.InteropServices.DllImport("user32.dll")]
    private static extern bool UpdateWindow(IntPtr hwnd);

    [System.Runtime.InteropServices.DllImport("user32.dll")]
    private static extern IntPtr DefWindowProcW(IntPtr hwnd, uint message, IntPtr wParam, IntPtr lParam);

    [System.Runtime.InteropServices.DllImport("user32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode)]
    private static extern int GetMessageW(out BeaconMessage message, IntPtr hwnd, uint min, uint max);

    [System.Runtime.InteropServices.DllImport("user32.dll")]
    private static extern bool TranslateMessage(ref BeaconMessage message);

    [System.Runtime.InteropServices.DllImport("user32.dll")]
    private static extern IntPtr DispatchMessageW(ref BeaconMessage message);

    [System.Runtime.InteropServices.DllImport("user32.dll")]
    private static extern IntPtr SendMessageW(IntPtr hwnd, uint message, IntPtr wParam, IntPtr lParam);

    [System.Runtime.InteropServices.DllImport("user32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode)]
    private static extern int GetWindowTextLengthW(IntPtr hwnd);

    [System.Runtime.InteropServices.DllImport("user32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode)]
    private static extern int GetWindowTextW(IntPtr hwnd, System.Text.StringBuilder text, int maximum);

    [System.Runtime.InteropServices.DllImport("user32.dll")]
    private static extern IntPtr LoadCursorW(IntPtr instance, IntPtr cursorName);

    [System.Runtime.InteropServices.DllImport("kernel32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode)]
    private static extern IntPtr GetModuleHandleW(string? moduleName);

    [System.Runtime.InteropServices.DllImport("gdi32.dll")]
    private static extern IntPtr GetStockObject(int objectId);

    private static void BeaconRequireWindows()
    {
        if (!OperatingSystem.IsWindows())
            throw new Exception("std.window is currently available on Windows only");
    }

    private static int BeaconInteger(object? value, string name)
    {
        if (value is not double number || number != Math.Truncate(number) || number < int.MinValue || number > int.MaxValue)
            throw new Exception($"{name} must be an integer Number");
        return (int)number;
    }

    private static int BeaconRecordInteger(BRecord record, string name, int fallback)
    {
        if (!record.TryGetValue(name, out var value)) return fallback;
        return BeaconInteger(value, name);
    }

    private static string BeaconRecordString(BRecord record, string name, string fallback)
    {
        if (!record.TryGetValue(name, out var value)) return fallback;
        return value as string ?? throw new Exception($"{name} must be a String");
    }

    private static BeaconNativeWindow BeaconWindowState(object? value)
    {
        var id = BeaconInteger(value, "window id");
        if (!BeaconWindows.TryGetValue(id, out var state))
            throw new Exception($"Unknown window id: {id}");
        return state;
    }

    private static void BeaconEnsureWindowClass()
    {
        if (BeaconWindowClassRegistered) return;
        var instance = GetModuleHandleW(null);
        var windowClass = new BeaconWindowClass
        {
            style = 0,
            lpfnWndProc = System.Runtime.InteropServices.Marshal.GetFunctionPointerForDelegate(BeaconWindowProcedure),
            cbClsExtra = 0,
            cbWndExtra = 0,
            hInstance = instance,
            hIcon = IntPtr.Zero,
            hCursor = LoadCursorW(IntPtr.Zero, (IntPtr)32512),
            hbrBackground = (IntPtr)6,
            lpszMenuName = null,
            lpszClassName = BeaconWindowClassName,
        };
        var atom = RegisterClassW(ref windowClass);
        if (atom == 0)
        {
            var error = System.Runtime.InteropServices.Marshal.GetLastWin32Error();
            if (error != 1410) throw new Exception($"Unable to register Beacon window class: Win32 error {error}");
        }
        BeaconWindowClassRegistered = true;
    }

    private static BRecord BeaconEvent(string type) => new() { ["type"] = type };

    private static IntPtr BeaconNativeWindowProc(IntPtr hwnd, uint message, IntPtr wParam, IntPtr lParam)
    {
        if (BeaconWindowsByHandle.TryGetValue(hwnd, out var state))
        {
            if (message == BeaconWmClose)
            {
                state.Events.Enqueue(BeaconEvent("close"));
                DestroyWindow(hwnd);
                return IntPtr.Zero;
            }
            if (message == BeaconWmDestroy)
                return IntPtr.Zero;
            if (message == BeaconWmSize)
            {
                var packed = unchecked((ulong)lParam.ToInt64());
                var width = (int)(packed & 0xFFFF);
                var height = (int)((packed >> 16) & 0xFFFF);
                state.Events.Enqueue(new BRecord { ["type"] = "resize", ["width"] = (double)width, ["height"] = (double)height });
                return IntPtr.Zero;
            }
            if (message == BeaconWmCommand)
            {
                var packed = unchecked((ulong)wParam.ToInt64());
                var controlId = (int)(packed & 0xFFFF);
                var notification = (int)((packed >> 16) & 0xFFFF);
                if (state.Actions.TryGetValue(controlId, out var action) && state.Kinds.TryGetValue(controlId, out var kind))
                {
                    if (kind == "button" && notification == 0)
                    {
                        state.Events.Enqueue(new BRecord { ["type"] = "action", ["action"] = action });
                        return IntPtr.Zero;
                    }
                    if (kind == "input" && notification == BeaconEnChange)
                    {
                        var length = GetWindowTextLengthW(lParam);
                        var builder = new System.Text.StringBuilder(length + 1);
                        GetWindowTextW(lParam, builder, builder.Capacity);
                        state.Events.Enqueue(new BRecord { ["type"] = "input", ["action"] = action, ["value"] = builder.ToString() });
                        return IntPtr.Zero;
                    }
                }
            }
            if (message == BeaconWmKeyDown || message == BeaconWmKeyUp)
            {
                state.Events.Enqueue(new BRecord
                {
                    ["type"] = message == BeaconWmKeyDown ? "keyDown" : "keyUp",
                    ["key"] = (double)wParam.ToInt64(),
                });
            }
            if (message == BeaconWmMouseMove || message == BeaconWmLeftDown || message == BeaconWmLeftUp)
            {
                var packed = unchecked((ulong)lParam.ToInt64());
                var x = unchecked((short)(packed & 0xFFFF));
                var y = unchecked((short)((packed >> 16) & 0xFFFF));
                var type = message == BeaconWmMouseMove ? "mouseMove" : message == BeaconWmLeftDown ? "mouseDown" : "mouseUp";
                state.Events.Enqueue(new BRecord { ["type"] = type, ["x"] = (double)x, ["y"] = (double)y });
            }
        }
        return DefWindowProcW(hwnd, message, wParam, lParam);
    }

    private static object? BeaconCreateWindow(object? payload)
    {
        if (payload is not BRecord config) throw new Exception("window create payload must be a Record");
        BeaconEnsureWindowClass();
        var title = BeaconRecordString(config, "title", "Beacon");
        var width = BeaconRecordInteger(config, "width", 1024);
        var height = BeaconRecordInteger(config, "height", 720);
        var instance = GetModuleHandleW(null);
        var handle = CreateWindowExW(
            0,
            BeaconWindowClassName,
            title,
            0x00CF0000,
            unchecked((int)0x80000000),
            unchecked((int)0x80000000),
            width,
            height,
            IntPtr.Zero,
            IntPtr.Zero,
            instance,
            IntPtr.Zero);
        if (handle == IntPtr.Zero)
            throw new Exception($"Unable to create Beacon window: Win32 error {System.Runtime.InteropServices.Marshal.GetLastWin32Error()}");
        var id = BeaconNextWindowId++;
        var state = new BeaconNativeWindow { Id = id, Handle = handle };
        BeaconWindows[id] = state;
        BeaconWindowsByHandle[handle] = state;
        return (double)id;
    }

    private static object? BeaconShowWindow(object? payload)
    {
        var state = BeaconWindowState(payload);
        ShowWindow(state.Handle, 5);
        UpdateWindow(state.Handle);
        return null;
    }

    private static object? BeaconCloseWindow(object? payload)
    {
        var state = BeaconWindowState(payload);
        state.Events.Enqueue(BeaconEvent("close"));
        DestroyWindow(state.Handle);
        return null;
    }

    private static object? BeaconNextEvent(object? payload)
    {
        var state = BeaconWindowState(payload);
        while (true)
        {
            if (state.Events.Count > 0)
            {
                var value = state.Events.Dequeue();
                if (value.TryGetValue("type", out var type) && type as string == "close")
                {
                    BeaconWindows.Remove(state.Id);
                    BeaconWindowsByHandle.Remove(state.Handle);
                }
                return value;
            }

            var result = GetMessageW(out var message, IntPtr.Zero, 0, 0);
            if (result < 0) throw new Exception("Unable to read native window event");
            if (result == 0) return BeaconEvent("close");
            TranslateMessage(ref message);
            DispatchMessageW(ref message);
        }
    }

    private static object? BeaconApplyControls(object? payload)
    {
        if (payload is not BRecord request) throw new Exception("window controls payload must be a Record");
        if (!request.TryGetValue("id", out var idValue)) throw new Exception("window controls payload requires id");
        if (!request.TryGetValue("controls", out var controlsValue) || controlsValue is not System.Collections.Generic.List<object?> controls)
            throw new Exception("window controls payload requires a List of controls");
        var state = BeaconWindowState(idValue);

        foreach (var control in state.Controls) DestroyWindow(control);
        state.Controls.Clear();
        state.Actions.Clear();
        state.Kinds.Clear();

        var instance = GetModuleHandleW(null);
        foreach (var value in controls)
        {
            if (value is not BRecord control) throw new Exception("UI control must be a Record");
            var kind = BeaconRecordString(control, "kind", "");
            var text = BeaconRecordString(control, "text", "");
            var action = BeaconRecordString(control, "action", "");
            var x = BeaconRecordInteger(control, "x", 0);
            var y = BeaconRecordInteger(control, "y", 0);
            var width = Math.Max(1, BeaconRecordInteger(control, "width", 1));
            var height = Math.Max(1, BeaconRecordInteger(control, "height", 1));

            string className;
            uint style = 0x40000000 | 0x10000000;
            uint extendedStyle = 0;
            var controlId = 0;

            if (kind == "text" || kind == "heading")
            {
                className = "STATIC";
            }
            else if (kind == "panel")
            {
                className = "STATIC";
                style |= 0x00000012;
            }
            else if (kind == "button")
            {
                className = "BUTTON";
                style |= 0x00010000;
                controlId = BeaconNextControlId++;
            }
            else if (kind == "input")
            {
                className = "EDIT";
                style |= 0x00010000 | 0x00000080;
                extendedStyle = 0x00000200;
                controlId = BeaconNextControlId++;
            }
            else if (kind == "textArea")
            {
                className = "EDIT";
                style |= 0x00200000 | 0x00000004 | 0x00000040 | 0x00000800;
                extendedStyle = 0x00000200;
            }
            else
            {
                throw new Exception($"Unsupported native UI control kind: {kind}");
            }

            var handle = CreateWindowExW(
                extendedStyle,
                className,
                text,
                style,
                x,
                y,
                width,
                height,
                state.Handle,
                controlId == 0 ? IntPtr.Zero : (IntPtr)controlId,
                instance,
                IntPtr.Zero);
            if (handle == IntPtr.Zero)
                throw new Exception($"Unable to create native UI control '{kind}': Win32 error {System.Runtime.InteropServices.Marshal.GetLastWin32Error()}");

            SendMessageW(handle, BeaconWmSetFont, GetStockObject(17), (IntPtr)1);
            state.Controls.Add(handle);
            if (controlId != 0 && action != "")
            {
                state.Actions[controlId] = action;
                state.Kinds[controlId] = kind;
            }
        }
        return null;
    }

    public static object? HostWindow(object? actionValue, object? payload)
    {
        if (actionValue is not string action) throw new Exception("hostWindow() action must be a String");
        if (action == "available") return OperatingSystem.IsWindows();
        if (action == "platform") return OperatingSystem.IsWindows() ? "windows" : "unsupported";

        BeaconRequireWindows();
        return action switch
        {
            "create" => BeaconCreateWindow(payload),
            "show" => BeaconShowWindow(payload),
            "close" => BeaconCloseWindow(payload),
            "next" => BeaconNextEvent(payload),
            "controls" => BeaconApplyControls(payload),
            _ => throw new Exception($"Unknown hostWindow() action: {action}"),
        };
    }

'''


def patch_seed() -> None:
    path = Path("tools/seed-refresh/Beacon.Compiler/Program.cs")
    text = patch_else_if_parser(path.read_text())

    runtime_anchor = '    private static string PathArgument(object? value, string functionName) =>\n'
    host_character = '''    public static string HostCharacter(object? value)\n    {\n        if (value is not double number || number != Math.Truncate(number) ||\n            number < 0 || number > 0x10FFFF || (number >= 0xD800 && number <= 0xDFFF))\n            throw new Exception("hostCharacter() expects a valid Unicode scalar Number");\n        return char.ConvertFromUtf32((int)number);\n    }\n\n'''
    if text.count(runtime_anchor) != 1:
        raise SystemExit("Expected one Runtime PathArgument anchor")
    text = text.replace(runtime_anchor, host_character + WINDOW_RUNTIME + runtime_anchor, 1)

    lines = text.splitlines()
    updated = []
    method_info_count = 0
    for line in lines:
        updated.append(line)
        if 'private static readonly ' in line and 'NumberMethod = Method(nameof(Runtime.Number), typeof(object));' in line:
            updated.append(line.replace('NumberMethod', 'HostCharacterMethod').replace('Runtime.Number', 'Runtime.HostCharacter'))
            updated.append(line.replace('NumberMethod', 'HostWindowMethod').replace('Runtime.Number', 'Runtime.HostWindow').replace('typeof(object));', 'typeof(object), typeof(object));'))
            method_info_count += 1
    if method_info_count != 2:
        raise SystemExit(f"Expected two Number MethodInfo anchors, found {method_info_count}")
    text = "\n".join(updated) + "\n"

    resolver = '        "Runtime.Number" => NumberMethod,\n'
    if text.count(resolver) != 1:
        raise SystemExit("Expected one Runtime.Number resolver entry")
    text = text.replace(
        resolver,
        resolver + '        "Runtime.HostCharacter" => HostCharacterMethod,\n        "Runtime.HostWindow" => HostWindowMethod,\n',
        1,
    )

    number_call = re.compile(
        r'''(        if \(callee is Atom \{ Kind: AtomKind\.Symbol \} numberAtom && numberAtom\.Text == "number"\)\n        \{\n.*?            return;\n        \}\n)''',
        re.S,
    )
    matches = list(number_call.finditer(text))
    if len(matches) != 1:
        raise SystemExit(f"Expected one direct number() call block, found {len(matches)}")
    host_calls = '''\n        if (callee is Atom { Kind: AtomKind.Symbol } hostCharacterAtom && hostCharacterAtom.Text == "hostCharacter")\n        {\n            if (args.Length != 1) throw new Exception("hostCharacter() expects one argument");\n            EmitExpr(args[0], ctx);\n            ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, HostCharacterMethod);\n            return;\n        }\n\n        if (callee is Atom { Kind: AtomKind.Symbol } hostWindowAtom && hostWindowAtom.Text == "hostWindow")\n        {\n            if (args.Length != 2) throw new Exception("hostWindow() expects two arguments");\n            EmitExpr(args[0], ctx);\n            EmitExpr(args[1], ctx);\n            ctx.IL.Emit(System.Reflection.Emit.OpCodes.Call, HostWindowMethod);\n            return;\n        }\n'''
    text = number_call.sub(lambda match: match.group(1) + host_calls, text, count=1)
    path.write_text(text)


if len(sys.argv) != 2 or sys.argv[1] not in {"beacon", "seed"}:
    raise SystemExit("usage: refresh-window-ui-seed.py beacon|seed")

if sys.argv[1] == "beacon":
    patch_emitter()
else:
    patch_seed()
