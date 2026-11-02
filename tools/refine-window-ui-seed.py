from pathlib import Path


PATH = Path("tools/seed-refresh/Beacon.Compiler/Program.cs")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one {label} match, found {count}")
    return text.replace(old, new, 1)


text = PATH.read_text()

text = replace_once(
    text,
    '''        public System.Collections.Generic.Dictionary<int, string> Actions { get; } = new();
        public System.Collections.Generic.Dictionary<int, string> Kinds { get; } = new();
''',
    '''        public System.Collections.Generic.Dictionary<int, string> Actions { get; } = new();
        public System.Collections.Generic.Dictionary<int, string> Kinds { get; } = new();
        public System.Collections.Generic.Dictionary<IntPtr, string> ControlKinds { get; } = new();
        public System.Collections.Generic.Dictionary<IntPtr, string> ControlVariants { get; } = new();
        public System.Collections.Generic.Dictionary<IntPtr, bool> ControlSurfaces { get; } = new();
''',
    "native window control metadata",
)

text = replace_once(
    text,
    '''    [System.Runtime.InteropServices.StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential)]
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

''',
    '''    [System.Runtime.InteropServices.StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential)]
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

    [System.Runtime.InteropServices.StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential)]
    private struct BeaconRect
    {
        public int left;
        public int top;
        public int right;
        public int bottom;
    }

    [System.Runtime.InteropServices.StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential)]
    private struct BeaconDrawItem
    {
        public uint CtlType;
        public uint CtlID;
        public uint itemID;
        public uint itemAction;
        public uint itemState;
        public IntPtr hwndItem;
        public IntPtr hDC;
        public BeaconRect rcItem;
        public IntPtr itemData;
    }

''',
    "native drawing structs",
)

text = replace_once(
    text,
    '''    private const uint BeaconWmSetFont = 0x0030;
    private const int BeaconEnChange = 0x0300;
''',
    '''    private const uint BeaconWmSetFont = 0x0030;
    private const uint BeaconWmDrawItem = 0x002B;
    private const uint BeaconWmCtlColorEdit = 0x0133;
    private const uint BeaconWmCtlColorStatic = 0x0138;
    private const uint BeaconEmSetMargins = 0x00D3;
    private const uint BeaconEmSetReadOnly = 0x00CF;
    private const uint BeaconEmSetCueBanner = 0x1501;
    private const int BeaconEnChange = 0x0300;
    private const uint BeaconOdsSelected = 0x0001;
''',
    "native drawing constants",
)

text = replace_once(
    text,
    '''    [System.Runtime.InteropServices.DllImport("gdi32.dll")]
    private static extern IntPtr GetStockObject(int objectId);

''',
    '''    [System.Runtime.InteropServices.DllImport("gdi32.dll")]
    private static extern IntPtr GetStockObject(int objectId);

    [System.Runtime.InteropServices.DllImport("gdi32.dll")]
    private static extern IntPtr CreateSolidBrush(uint color);

    [System.Runtime.InteropServices.DllImport("gdi32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode)]
    private static extern IntPtr CreateFontW(int height, int width, int escapement, int orientation, int weight, uint italic, uint underline, uint strikeOut, uint charSet, uint outputPrecision, uint clipPrecision, uint quality, uint pitchAndFamily, string faceName);

    [System.Runtime.InteropServices.DllImport("gdi32.dll")]
    private static extern uint SetTextColor(IntPtr dc, uint color);

    [System.Runtime.InteropServices.DllImport("gdi32.dll")]
    private static extern uint SetBkColor(IntPtr dc, uint color);

    [System.Runtime.InteropServices.DllImport("gdi32.dll")]
    private static extern int SetBkMode(IntPtr dc, int mode);

    [System.Runtime.InteropServices.DllImport("gdi32.dll")]
    private static extern IntPtr SelectObject(IntPtr dc, IntPtr value);

    [System.Runtime.InteropServices.DllImport("user32.dll")]
    private static extern int FillRect(IntPtr dc, ref BeaconRect rect, IntPtr brush);

    [System.Runtime.InteropServices.DllImport("user32.dll")]
    private static extern int FrameRect(IntPtr dc, ref BeaconRect rect, IntPtr brush);

    [System.Runtime.InteropServices.DllImport("user32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode)]
    private static extern int DrawTextW(IntPtr dc, string text, int count, ref BeaconRect rect, uint format);

    [System.Runtime.InteropServices.DllImport("user32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode, EntryPoint = "SendMessageW")]
    private static extern IntPtr SendMessageTextW(IntPtr hwnd, uint message, IntPtr wParam, string lParam);

    [System.Runtime.InteropServices.DllImport("uxtheme.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode)]
    private static extern int SetWindowTheme(IntPtr hwnd, string? subAppName, string? subIdList);

    [System.Runtime.InteropServices.DllImport("dwmapi.dll")]
    private static extern int DwmSetWindowAttribute(IntPtr hwnd, int attribute, ref int value, int valueSize);

''',
    "native drawing APIs",
)

helpers = '''    private static uint BeaconColor(int red, int green, int blue) =>
        (uint)(red | (green << 8) | (blue << 16));

    private static readonly uint BeaconBackgroundColor = BeaconColor(12, 16, 22);
    private static readonly uint BeaconSurfaceColor = BeaconColor(21, 27, 36);
    private static readonly uint BeaconInputColor = BeaconColor(16, 22, 30);
    private static readonly uint BeaconBorderColor = BeaconColor(40, 50, 65);
    private static readonly uint BeaconTextColor = BeaconColor(237, 242, 247);
    private static readonly uint BeaconMutedColor = BeaconColor(147, 160, 178);
    private static readonly uint BeaconAccentColor = BeaconColor(91, 140, 255);
    private static readonly uint BeaconAccentPressedColor = BeaconColor(71, 118, 230);
    private static readonly uint BeaconButtonColor = BeaconColor(32, 41, 54);
    private static readonly uint BeaconButtonPressedColor = BeaconColor(42, 54, 70);

    private static readonly IntPtr BeaconBackgroundBrush = CreateSolidBrush(BeaconBackgroundColor);
    private static readonly IntPtr BeaconSurfaceBrush = CreateSolidBrush(BeaconSurfaceColor);
    private static readonly IntPtr BeaconInputBrush = CreateSolidBrush(BeaconInputColor);
    private static readonly IntPtr BeaconBorderBrush = CreateSolidBrush(BeaconBorderColor);
    private static readonly IntPtr BeaconAccentBrush = CreateSolidBrush(BeaconAccentColor);
    private static readonly IntPtr BeaconAccentPressedBrush = CreateSolidBrush(BeaconAccentPressedColor);
    private static readonly IntPtr BeaconButtonBrush = CreateSolidBrush(BeaconButtonColor);
    private static readonly IntPtr BeaconButtonPressedBrush = CreateSolidBrush(BeaconButtonPressedColor);

    private static IntPtr BeaconFont(int height, int weight, string family) =>
        CreateFontW(height, 0, 0, 0, weight, 0, 0, 0, 1, 0, 0, 5, 0, family);

    private static readonly IntPtr BeaconBodyFont = BeaconFont(-16, 400, "Segoe UI");
    private static readonly IntPtr BeaconHeadingFont = BeaconFont(-22, 600, "Segoe UI");
    private static readonly IntPtr BeaconCodeFont = BeaconFont(-15, 400, "Consolas");

    private static bool BeaconRecordBoolean(BRecord record, string name, bool fallback)
    {
        if (!record.TryGetValue(name, out var value)) return fallback;
        return value is bool boolean ? boolean : throw new Exception($"{name} must be a Boolean");
    }

    private static void BeaconApplyWindowChrome(IntPtr handle)
    {
        SetWindowTheme(handle, "DarkMode_Explorer", null);
        var dark = 1;
        if (DwmSetWindowAttribute(handle, 20, ref dark, sizeof(int)) != 0)
            DwmSetWindowAttribute(handle, 19, ref dark, sizeof(int));
        var corner = 2;
        DwmSetWindowAttribute(handle, 33, ref corner, sizeof(int));
        var border = unchecked((int)BeaconBorderColor);
        var caption = unchecked((int)BeaconBackgroundColor);
        var text = unchecked((int)BeaconTextColor);
        DwmSetWindowAttribute(handle, 34, ref border, sizeof(int));
        DwmSetWindowAttribute(handle, 35, ref caption, sizeof(int));
        DwmSetWindowAttribute(handle, 36, ref text, sizeof(int));
    }

    private static void BeaconDrawControl(BeaconNativeWindow state, IntPtr lParam)
    {
        var item = System.Runtime.InteropServices.Marshal.PtrToStructure<BeaconDrawItem>(lParam);
        if (!state.ControlKinds.TryGetValue(item.hwndItem, out var kind)) return;

        if (kind == "panel")
        {
            FillRect(item.hDC, ref item.rcItem, BeaconSurfaceBrush);
            FrameRect(item.hDC, ref item.rcItem, BeaconBorderBrush);
            return;
        }

        if (kind != "button") return;
        state.ControlVariants.TryGetValue(item.hwndItem, out var variant);
        var selected = (item.itemState & BeaconOdsSelected) != 0;
        var primary = variant == "primary";
        var brush = primary
            ? (selected ? BeaconAccentPressedBrush : BeaconAccentBrush)
            : (selected ? BeaconButtonPressedBrush : BeaconButtonBrush);
        FillRect(item.hDC, ref item.rcItem, brush);
        FrameRect(item.hDC, ref item.rcItem, primary ? BeaconAccentBrush : BeaconBorderBrush);

        var length = GetWindowTextLengthW(item.hwndItem);
        var builder = new System.Text.StringBuilder(length + 1);
        GetWindowTextW(item.hwndItem, builder, builder.Capacity);
        SetBkMode(item.hDC, 1);
        SetTextColor(item.hDC, BeaconTextColor);
        var previousFont = SelectObject(item.hDC, BeaconBodyFont);
        var textRect = item.rcItem;
        DrawTextW(item.hDC, builder.ToString(), -1, ref textRect, 0x00000025);
        SelectObject(item.hDC, previousFont);
    }

'''

text = replace_once(
    text,
    '''    private static void BeaconRequireWindows()
''',
    helpers + '''    private static void BeaconRequireWindows()
''',
    "native theme helpers",
)

text = replace_once(text, '            hbrBackground = (IntPtr)6,\n', '            hbrBackground = BeaconBackgroundBrush,\n', "window background brush")

proc_anchor = '''        if (BeaconWindowsByHandle.TryGetValue(hwnd, out var state))
        {
'''
proc_addition = proc_anchor + '''            if (message == BeaconWmCtlColorStatic)
            {
                var dc = wParam;
                SetBkMode(dc, 1);
                if (state.ControlKinds.TryGetValue(lParam, out var controlKind) && controlKind == "muted")
                    SetTextColor(dc, BeaconMutedColor);
                else
                    SetTextColor(dc, BeaconTextColor);
                return state.ControlSurfaces.TryGetValue(lParam, out var surface) && surface
                    ? BeaconSurfaceBrush
                    : BeaconBackgroundBrush;
            }
            if (message == BeaconWmCtlColorEdit)
            {
                SetTextColor(wParam, BeaconTextColor);
                SetBkColor(wParam, BeaconInputColor);
                return BeaconInputBrush;
            }
            if (message == BeaconWmDrawItem)
            {
                BeaconDrawControl(state, lParam);
                return (IntPtr)1;
            }
'''
text = replace_once(text, proc_anchor, proc_addition, "window paint message handling")

text = replace_once(
    text,
    '''        BeaconWindows[id] = state;
        BeaconWindowsByHandle[handle] = state;
        return (double)id;
''',
    '''        BeaconWindows[id] = state;
        BeaconWindowsByHandle[handle] = state;
        BeaconApplyWindowChrome(handle);
        return (double)id;
''',
    "window chrome application",
)

text = replace_once(
    text,
    '''        state.Controls.Clear();
        state.Actions.Clear();
        state.Kinds.Clear();
''',
    '''        state.Controls.Clear();
        state.Actions.Clear();
        state.Kinds.Clear();
        state.ControlKinds.Clear();
        state.ControlVariants.Clear();
        state.ControlSurfaces.Clear();
''',
    "control metadata reset",
)

text = replace_once(
    text,
    '''            var action = BeaconRecordString(control, "action", "");
            var x = BeaconRecordInteger(control, "x", 0);
''',
    '''            var action = BeaconRecordString(control, "action", "");
            var variant = BeaconRecordString(control, "variant", "secondary");
            var placeholder = BeaconRecordString(control, "placeholder", "");
            var surface = BeaconRecordBoolean(control, "surface", false);
            var x = BeaconRecordInteger(control, "x", 0);
''',
    "control visual metadata",
)

old_kinds = '''            if (kind == "text" || kind == "heading")
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
'''
new_kinds = '''            if (kind == "text" || kind == "muted" || kind == "heading")
            {
                className = "STATIC";
            }
            else if (kind == "panel")
            {
                className = "STATIC";
                style |= 0x0000000D;
            }
            else if (kind == "button")
            {
                className = "BUTTON";
                style |= 0x00010000 | 0x0000000B;
                controlId = BeaconNextControlId++;
            }
            else if (kind == "input")
            {
                className = "EDIT";
                style |= 0x00010000 | 0x00000080;
                controlId = BeaconNextControlId++;
            }
            else if (kind == "textArea" || kind == "code")
            {
                className = "EDIT";
                style |= 0x00200000 | 0x00000004 | 0x00000040 | 0x00001000;
                if (kind == "code") style |= 0x00000800;
            }
'''
text = replace_once(text, old_kinds, new_kinds, "polished control styles")

text = replace_once(
    text,
    '''            SendMessageW(handle, BeaconWmSetFont, GetStockObject(17), (IntPtr)1);
            state.Controls.Add(handle);
''',
    '''            var font = kind == "heading" ? BeaconHeadingFont : kind == "code" ? BeaconCodeFont : BeaconBodyFont;
            SendMessageW(handle, BeaconWmSetFont, font, (IntPtr)1);
            if (kind == "input" || kind == "textArea" || kind == "code")
            {
                SetWindowTheme(handle, "DarkMode_Explorer", null);
                SendMessageW(handle, BeaconEmSetMargins, (IntPtr)3, (IntPtr)((10 << 16) | 10));
            }
            if (kind == "input" && placeholder != "")
                SendMessageTextW(handle, BeaconEmSetCueBanner, (IntPtr)1, placeholder);
            if (kind == "code")
                SendMessageW(handle, BeaconEmSetReadOnly, (IntPtr)1, IntPtr.Zero);

            state.Controls.Add(handle);
            state.ControlKinds[handle] = kind;
            state.ControlVariants[handle] = variant;
            state.ControlSurfaces[handle] = surface;
''',
    "control typography and theme application",
)

PATH.write_text(text)
