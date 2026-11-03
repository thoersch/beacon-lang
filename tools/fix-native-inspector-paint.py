from pathlib import Path

path = Path("tools/seed-refresh/Beacon.Compiler/Program.cs")
text = path.read_text()

def replace_once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one {label}, found {count}")
    text = text.replace(old, new, 1)

replace_once(
'''        public System.Collections.Generic.Dictionary<IntPtr, bool> ControlSurfaces { get; } = new();
''',
'''        public System.Collections.Generic.Dictionary<IntPtr, bool> ControlSurfaces { get; } = new();
        public System.Collections.Generic.List<BeaconRect> PaintedPanels { get; } = new();
        public System.Collections.Generic.List<BeaconRect> InputFrames { get; } = new();
''',
"painted control geometry")

replace_once(
'''    private const uint BeaconWmDrawItem = 0x002B;
''',
'''    private const uint BeaconWmEraseBackground = 0x0014;
    private const uint BeaconWmDrawItem = 0x002B;
''',
"background paint constant")

replace_once(
'''    [System.Runtime.InteropServices.DllImport("gdi32.dll")]
    private static extern IntPtr CreateSolidBrush(uint color);
''',
'''    [System.Runtime.InteropServices.DllImport("user32.dll")]
    private static extern bool GetClientRect(IntPtr hwnd, out BeaconRect rect);

    [System.Runtime.InteropServices.DllImport("user32.dll")]
    private static extern bool InvalidateRect(IntPtr hwnd, IntPtr rect, bool erase);

    [System.Runtime.InteropServices.DllImport("gdi32.dll")]
    private static extern IntPtr CreateSolidBrush(uint color);
''',
"parent paint APIs")

replace_once(
'''        if (kind == "panel")
        {
            FillRect(item.hDC, ref item.rcItem, BeaconSurfaceBrush);
            FrameRect(item.hDC, ref item.rcItem, BeaconBorderBrush);
            return;
        }

''',
'''        // Panels are painted by the parent, never as foreground child windows.

''',
"remove foreground panel drawing")

replace_once(
'''        if (BeaconWindowsByHandle.TryGetValue(hwnd, out var state))
        {
            if (message == BeaconWmCtlColorStatic)
''',
'''        if (BeaconWindowsByHandle.TryGetValue(hwnd, out var state))
        {
            if (message == BeaconWmEraseBackground)
            {
                if (GetClientRect(hwnd, out var client))
                    FillRect(wParam, ref client, BeaconBackgroundBrush);
                foreach (var panel in state.PaintedPanels)
                {
                    var bounds = panel;
                    FillRect(wParam, ref bounds, BeaconSurfaceBrush);
                    FrameRect(wParam, ref bounds, BeaconBorderBrush);
                }
                foreach (var input in state.InputFrames)
                {
                    var bounds = input;
                    FillRect(wParam, ref bounds, BeaconInputBrush);
                    FrameRect(wParam, ref bounds, BeaconBorderBrush);
                }
                return (IntPtr)1;
            }
            if (message == BeaconWmCtlColorStatic)
''',
"paint parent surfaces behind children")

replace_once(
'''                SetBkMode(dc, 1);
                if (state.ControlKinds.TryGetValue(lParam, out var controlKind) && controlKind == "muted")
                    SetTextColor(dc, BeaconMutedColor);
                else
                    SetTextColor(dc, BeaconTextColor);
                return state.ControlSurfaces.TryGetValue(lParam, out var surface) && surface
                    ? BeaconSurfaceBrush
                    : BeaconBackgroundBrush;
''',
'''                SetBkMode(dc, 1);
                state.ControlKinds.TryGetValue(lParam, out var controlKind);
                if (controlKind == "code")
                {
                    SetTextColor(dc, BeaconTextColor);
                    SetBkColor(dc, BeaconInputColor);
                    return BeaconInputBrush;
                }
                SetTextColor(dc, controlKind == "muted" ? BeaconMutedColor : BeaconTextColor);
                return state.ControlSurfaces.TryGetValue(lParam, out var surface) && surface
                    ? BeaconSurfaceBrush
                    : BeaconBackgroundBrush;
''',
"read-only code text and background colors")

replace_once(
'''            0x00CF0000,
''',
'''            0x00CF0000 | 0x02000000, // WS_CLIPCHILDREN: never paint over native text and input controls.
''',
"clip parent painting around children")

replace_once(
'''        state.ControlSurfaces.Clear();
''',
'''        state.ControlSurfaces.Clear();
        state.PaintedPanels.Clear();
        state.InputFrames.Clear();
''',
"reset parent-painted surfaces")

replace_once(
'''            var height = Math.Max(1, BeaconRecordInteger(control, "height", 1));

            string className;
''',
'''            var height = Math.Max(1, BeaconRecordInteger(control, "height", 1));

            // Structural panels are background surfaces. They must never own HWNDs:
            // a full-size STATIC child would cover the labels and editors inside it.
            if (kind == "panel")
            {
                state.PaintedPanels.Add(new BeaconRect
                {
                    left = x, top = y, right = x + width, bottom = y + height
                });
                continue;
            }

            // The parent paints input frames; their native EDIT children sit inside
            // the border. Single-line inputs are vertically centered in a 40px row.
            if (kind == "input" || kind == "textArea" || kind == "code")
            {
                state.InputFrames.Add(new BeaconRect
                {
                    left = x, top = y, right = x + width, bottom = y + height
                });
                x += 1;
                width = Math.Max(1, width - 2);
                if (kind == "input")
                {
                    y += 6;
                    height = Math.Max(1, height - 12);
                }
                else
                {
                    y += 1;
                    height = Math.Max(1, height - 2);
                }
            }

            string className;
''',
"separate structural panel and framed input layout")

replace_once(
'''            else if (kind == "panel")
            {
                className = "STATIC";
                style |= 0x0000000D;
            }
''',
'''            // Panel background geometry is handled above.
''',
"remove panel HWND creation")

replace_once(
'''            var handle = CreateWindowExW(
                extendedStyle,
                className,
                text,
''',
'''            // Win32 multiline EDIT controls require CRLF, not LF-only Beacon text.
            var nativeText = kind == "code" || kind == "textArea"
                ? text.Replace("\\r\\n", "\\n").Replace('\\r', '\\n').Replace("\\n", "\\r\\n")
                : text;
            var handle = CreateWindowExW(
                extendedStyle,
                className,
                nativeText,
''',
"normalize multiline editor text")

replace_once(
'''            state.ControlSurfaces[handle] = surface;
''',
'''            state.ControlSurfaces[handle] = surface;
''',
"assert native metadata anchor")

replace_once(
'''        }
        return null;
    }

    public static object? HostWindow(object? actionValue, object? payload)
''',
'''        }
        InvalidateRect(state.Handle, IntPtr.Zero, true);
        return null;
    }

    public static object? HostWindow(object? actionValue, object? payload)
''',
"request parent repaint after control mounting")

path.write_text(text)
