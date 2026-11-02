from pathlib import Path

path = Path("tools/seed-refresh/Beacon.Compiler/Program.cs")
text = path.read_text()

old = '''    private static readonly IntPtr BeaconBackgroundBrush = CreateSolidBrush(BeaconBackgroundColor);
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
'''

new = '''    private static IntPtr BeaconBackgroundBrush;
    private static IntPtr BeaconSurfaceBrush;
    private static IntPtr BeaconInputBrush;
    private static IntPtr BeaconBorderBrush;
    private static IntPtr BeaconAccentBrush;
    private static IntPtr BeaconAccentPressedBrush;
    private static IntPtr BeaconButtonBrush;
    private static IntPtr BeaconButtonPressedBrush;
    private static IntPtr BeaconBodyFont;
    private static IntPtr BeaconHeadingFont;
    private static IntPtr BeaconCodeFont;

    private static IntPtr BeaconFont(int height, int weight, string family) =>
        CreateFontW(height, 0, 0, 0, weight, 0, 0, 0, 1, 0, 0, 5, 0, family);

    private static void BeaconEnsureVisualResources()
    {
        if (BeaconBackgroundBrush != IntPtr.Zero) return;
        BeaconRequireWindows();
        BeaconBackgroundBrush = CreateSolidBrush(BeaconBackgroundColor);
        BeaconSurfaceBrush = CreateSolidBrush(BeaconSurfaceColor);
        BeaconInputBrush = CreateSolidBrush(BeaconInputColor);
        BeaconBorderBrush = CreateSolidBrush(BeaconBorderColor);
        BeaconAccentBrush = CreateSolidBrush(BeaconAccentColor);
        BeaconAccentPressedBrush = CreateSolidBrush(BeaconAccentPressedColor);
        BeaconButtonBrush = CreateSolidBrush(BeaconButtonColor);
        BeaconButtonPressedBrush = CreateSolidBrush(BeaconButtonPressedColor);
        BeaconBodyFont = BeaconFont(-16, 400, "Segoe UI");
        BeaconHeadingFont = BeaconFont(-22, 600, "Segoe UI");
        BeaconCodeFont = BeaconFont(-15, 400, "Consolas");
    }
'''

if text.count(old) != 1:
    raise SystemExit("Expected eager native visual resource block")
text = text.replace(old, new, 1)

old_init = '''    private static void BeaconEnsureWindowClass()
    {
        if (BeaconWindowClassRegistered) return;
        var instance = GetModuleHandleW(null);
'''
new_init = '''    private static void BeaconEnsureWindowClass()
    {
        if (BeaconWindowClassRegistered) return;
        BeaconEnsureVisualResources();
        var instance = GetModuleHandleW(null);
'''
if text.count(old_init) != 1:
    raise SystemExit("Expected native window class initialization block")
text = text.replace(old_init, new_init, 1)

path.write_text(text)
