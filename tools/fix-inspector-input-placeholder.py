from pathlib import Path

path = Path("tools/seed-refresh/Beacon.Compiler/Program.cs")
text = path.read_text()

def change(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one {label}, found {count}")
    text = text.replace(old, new, 1)

change(
'''    private const uint BeaconWmEraseBackground = 0x0014;
''',
'''    private const uint BeaconWmEraseBackground = 0x0014;
    private const uint BeaconWmPaint = 0x000F;
    private const uint BeaconWmNcDestroy = 0x0082;
''',
"edit painting message constants")

change(
'''    [System.Runtime.InteropServices.DllImport("user32.dll")]
    private static extern bool InvalidateRect(IntPtr hwnd, IntPtr rect, bool erase);
''',
'''    [System.Runtime.InteropServices.DllImport("user32.dll")]
    private static extern bool InvalidateRect(IntPtr hwnd, IntPtr rect, bool erase);

    [System.Runtime.InteropServices.DllImport("user32.dll", EntryPoint = "SetWindowLongPtrW", SetLastError = true)]
    private static extern IntPtr SetWindowLongPtrW(IntPtr hwnd, int index, IntPtr value);

    [System.Runtime.InteropServices.DllImport("user32.dll", EntryPoint = "CallWindowProcW")]
    private static extern IntPtr CallWindowProcW(IntPtr previous, IntPtr hwnd, uint message, IntPtr wParam, IntPtr lParam);

    [System.Runtime.InteropServices.DllImport("user32.dll")]
    private static extern IntPtr GetDC(IntPtr hwnd);

    [System.Runtime.InteropServices.DllImport("user32.dll")]
    private static extern int ReleaseDC(IntPtr hwnd, IntPtr dc);
''',
"native EDIT subclass APIs")

anchor='''    private static void BeaconDrawControl(BeaconNativeWindow state, IntPtr lParam)
'''
callback='''    // Paint the input placeholder in Beacon's muted theme color. The Win32
    // cue-banner API can silently render invisible text under dark edit themes.
    // Subclassing just EDIT preserves native typing, selection and focus behavior.
    private static readonly BeaconWindowProcDelegate BeaconInputPlaceholderProcedure = BeaconNativeInputPlaceholderProc;
    private static readonly System.Collections.Generic.Dictionary<IntPtr, IntPtr> BeaconInputOriginalProcedures = new();
    private static readonly System.Collections.Generic.Dictionary<IntPtr, string> BeaconInputPlaceholderText = new();

    private static IntPtr BeaconNativeInputPlaceholderProc(IntPtr hwnd, uint message, IntPtr wParam, IntPtr lParam)
    {
        if (!BeaconInputOriginalProcedures.TryGetValue(hwnd, out var previous))
            return DefWindowProcW(hwnd, message, wParam, lParam);

        var result = CallWindowProcW(previous, hwnd, message, wParam, lParam);
        if (message == BeaconWmPaint &&
            BeaconInputPlaceholderText.TryGetValue(hwnd, out var hint) &&
            hint.Length > 0 &&
            GetWindowTextLengthW(hwnd) == 0)
        {
            var dc = GetDC(hwnd);
            if (dc != IntPtr.Zero)
            {
                try
                {
                    if (GetClientRect(hwnd, out var bounds))
                    {
                        bounds.left += 10;
                        bounds.right -= 8;
                        var previousFont = SelectObject(dc, BeaconBodyFont);
                        var previousColor = SetTextColor(dc, BeaconMutedColor);
                        var previousMode = SetBkMode(dc, 1);
                        DrawTextW(dc, hint, -1, ref bounds, 0x00000024); // DT_SINGLELINE | DT_VCENTER
                        SetBkMode(dc, previousMode);
                        SetTextColor(dc, previousColor);
                        SelectObject(dc, previousFont);
                    }
                }
                finally { ReleaseDC(hwnd, dc); }
            }
        }
        if (message == BeaconWmNcDestroy)
        {
            BeaconInputOriginalProcedures.Remove(hwnd);
            BeaconInputPlaceholderText.Remove(hwnd);
        }
        return result;
    }

'''
change(anchor, callback+anchor, "themed input placeholder callback")

change(
'''            if (kind == "input" && placeholder != "")
                SendMessageTextW(handle, BeaconEmSetCueBanner, (IntPtr)1, placeholder);
''',
'''            if (kind == "input" && placeholder != "")
            {
                // Native cue banners are unreliable in dark Win32 EDIT controls.
                BeaconInputPlaceholderText[handle] = placeholder;
                var wndproc = System.Runtime.InteropServices.Marshal.GetFunctionPointerForDelegate(BeaconInputPlaceholderProcedure);
                var previousProc = SetWindowLongPtrW(handle, -4, wndproc); // GWLP_WNDPROC
                if (previousProc == IntPtr.Zero)
                    throw new Exception("Unable to install Beacon input placeholder renderer");
                BeaconInputOriginalProcedures[handle] = previousProc;
                InvalidateRect(handle, IntPtr.Zero, true);
            }
''',
"replace unreliable native cue banner with themed EDIT placeholder painting")

path.write_text(text)
