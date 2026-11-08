using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text.Json;
using System.Threading.Tasks;

namespace Beacon.Native;

// The independent Windows OpenGL 1.1 binding module. No graphics package
// dependencies; all GL functions are provided by the driver via opengl32.dll.
// The generic Beacon host communicates through a JSON ABI v1 entry point.
public static class Extension
{
    public static int AbiVersion => 1;

    private sealed class Context
    {
        public required int Id { get; init; }
        public required IntPtr Window { get; init; }
        public required IntPtr Dc { get; init; }
        public required IntPtr Glrc { get; init; }
        public required int OwnerThread { get; init; }
        public required string Version { get; init; }
    }

    // Force the Windows OpenGL ICD to initialize BEFORE selecting a pixel
    // format. .NET P/Invoke libraries load lazily; without preloading opengl32
    // SetPixelFormat can report success while GetPixelFormat still returns 0.
    private static IntPtr OpenGlModule;
    private static void EnsureOpenGlLoaded()
    {
        if (OpenGlModule == IntPtr.Zero)
            OpenGlModule = NativeLibrary.Load("opengl32.dll");
    }

    private static readonly Dictionary<int, Context> Contexts = new();
    private static int NextId = 1;

    private const uint PfdDrawToWindow = 0x00000004;
    private const uint PfdSupportOpenGl = 0x00000020;
    private const uint PfdDoubleBuffer = 0x00000001;
    private const uint GlColorBufferBit = 0x00004000;
    private const uint GlTriangles = 0x0004;
    private const uint GlQuads = 0x0007;
    private const uint GlTriangleFan = 0x0006;
    private const uint GlProjection = 0x1701;
    private const uint GlModelview = 0x1700;
    private const uint GlVersion = 0x1F02;
    private const uint GlRgba = 0x1908;
    private const uint GlUnsignedByte = 0x1401;

    [StructLayout(LayoutKind.Sequential)]
    private struct PixelFormatDescriptor
    {
        public ushort nSize;
        public ushort nVersion;
        public uint dwFlags;
        public byte iPixelType;
        public byte cColorBits;
        public byte cRedBits;
        public byte cRedShift;
        public byte cGreenBits;
        public byte cGreenShift;
        public byte cBlueBits;
        public byte cBlueShift;
        public byte cAlphaBits;
        public byte cAlphaShift;
        public byte cAccumBits;
        public byte cAccumRedBits;
        public byte cAccumGreenBits;
        public byte cAccumBlueBits;
        public byte cAccumAlphaBits;
        public byte cDepthBits;
        public byte cStencilBits;
        public byte cAuxBuffers;
        public byte iLayerType;
        public byte bReserved;
        public uint dwLayerMask;
        public uint dwVisibleMask;
        public uint dwDamageMask;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct Rect { public int left, top, right, bottom; }

    // Generic delayed wake for programs using the blocking Win32 event queue.
    // Reserved mouse coordinates (32766, token) identify scheduled wakeups.
    // Tokens let callers ignore stale events after undo or reset.
    private const uint WmMouseMove = 0x0200;
    private const int WakeMarkerX = 32766;
    [DllImport("user32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool PostMessage(IntPtr hwnd, uint message, IntPtr wparam, IntPtr lparam);
    [DllImport("user32.dll", SetLastError = true)]
    private static extern IntPtr GetDC(IntPtr hwnd);
    [DllImport("user32.dll", SetLastError = true)]
    private static extern int ReleaseDC(IntPtr hwnd, IntPtr dc);
    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool IsWindow(IntPtr hwnd);
    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetClientRect(IntPtr hwnd, out Rect rect);

    [DllImport("gdi32.dll", SetLastError = true)]
    private static extern int ChoosePixelFormat(IntPtr dc, ref PixelFormatDescriptor descriptor);
    [DllImport("gdi32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool SetPixelFormat(IntPtr dc, int format, ref PixelFormatDescriptor descriptor);
    [DllImport("gdi32.dll", SetLastError = true)]
    private static extern int GetPixelFormat(IntPtr dc);
    [DllImport("gdi32.dll", SetLastError = true)]
    private static extern int DescribePixelFormat(IntPtr dc, int format, uint descriptorSize, ref PixelFormatDescriptor descriptor);
    [DllImport("gdi32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool SwapBuffers(IntPtr dc);

    [DllImport("opengl32.dll", SetLastError = true)]
    private static extern IntPtr wglCreateContext(IntPtr dc);
    [DllImport("opengl32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool wglMakeCurrent(IntPtr dc, IntPtr glrc);
    [DllImport("opengl32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool wglDeleteContext(IntPtr glrc);
    [DllImport("opengl32.dll", EntryPoint = "glGetString")]
    private static extern IntPtr GlGetString(uint name);
    [DllImport("opengl32.dll", EntryPoint = "glViewport")]
    private static extern void GlViewport(int x, int y, int width, int height);
    [DllImport("opengl32.dll", EntryPoint = "glMatrixMode")]
    private static extern void GlMatrixMode(uint mode);
    [DllImport("opengl32.dll", EntryPoint = "glLoadIdentity")]
    private static extern void GlLoadIdentity();
    [DllImport("opengl32.dll", EntryPoint = "glOrtho")]
    private static extern void GlOrtho(double left, double right, double bottom, double top, double near, double far);
    [DllImport("opengl32.dll", EntryPoint = "glClearColor")]
    private static extern void GlClearColor(float red, float green, float blue, float alpha);
    [DllImport("opengl32.dll", EntryPoint = "glClear")]
    private static extern void GlClear(uint mask);
    [DllImport("opengl32.dll", EntryPoint = "glBegin")]
    private static extern void GlBegin(uint mode);
    [DllImport("opengl32.dll", EntryPoint = "glEnd")]
    private static extern void GlEnd();
    [DllImport("opengl32.dll", EntryPoint = "glColor3f")]
    private static extern void GlColor3f(float red, float green, float blue);
    [DllImport("opengl32.dll", EntryPoint = "glVertex2f")]
    private static extern void GlVertex2f(float x, float y);
    [DllImport("opengl32.dll", EntryPoint = "glFlush")]
    private static extern void GlFlush();
    [DllImport("opengl32.dll", EntryPoint = "glReadPixels")]
    private static extern void GlReadPixels(int x, int y, int width, int height,
        uint format, uint type, IntPtr destination);

    public static string Invoke(string json)
    {
        using var document = JsonDocument.Parse(json);
        var request = document.RootElement;
        if (request.ValueKind != JsonValueKind.Object)
            throw new InvalidOperationException("OpenGL extension request must be a Record");
        var action = String(request, "action");
        if (action == "available")
            return Reply(new { available = OperatingSystem.IsWindows() });
        if (!OperatingSystem.IsWindows())
            throw new PlatformNotSupportedException("std.graphics.gl currently requires Windows");

        return action switch
        {
            "create" => Reply(Create(request)),
            "destroy" => Reply(Destroy(request)),
            "clearColor" => Reply(ClearColor(request)),
            "clear" => Reply(Clear(request)),
            "viewport" => Reply(Viewport(request)),
            "triangle" => Reply(Triangle(request)),
            "batch" => Reply(Batch(request)),
            "wake" => Reply(Wake(request)),
            "present" => Reply(Present(request)),
            "samplePixel" => Reply(SamplePixel(request)),
            _ => throw new InvalidOperationException($"Unknown OpenGL operation: {action}"),
        };
    }

    private static string Reply(object? response) => JsonSerializer.Serialize(response);

    private static string String(JsonElement value, string field) =>
        value.GetProperty(field).GetString() ??
        throw new ArgumentException($"{field} must be a String");

    private static double Number(JsonElement value, string field)
    {
        var number = value.GetProperty(field).GetDouble();
        if (!double.IsFinite(number))
            throw new ArgumentException($"{field} must be finite");
        return number;
    }

    private static int Integer(JsonElement value, string field)
    {
        var number = Number(value, field);
        if (number != Math.Truncate(number) || number < int.MinValue || number > int.MaxValue)
            throw new ArgumentException($"{field} must be an integer");
        return (int)number;
    }

    private static Context Current(JsonElement request)
    {
        var id = Integer(request, "id");
        if (!Contexts.TryGetValue(id, out var state))
            throw new InvalidOperationException($"OpenGL context {id} has been destroyed or was never created");
        if (state.OwnerThread != Environment.CurrentManagedThreadId)
            throw new InvalidOperationException("OpenGL context operations must run on the thread that created it");
        if (!IsWindow(state.Window))
            throw new InvalidOperationException("OpenGL context window has been destroyed");
        if (!wglMakeCurrent(state.Dc, state.Glrc))
            throw new InvalidOperationException($"wglMakeCurrent failed ({Marshal.GetLastWin32Error()})");
        return state;
    }

    private static object Create(JsonElement request)
    {
        var handleText = String(request, "nativeHandle");
        if (!long.TryParse(handleText, System.Globalization.NumberStyles.HexNumber,
                System.Globalization.CultureInfo.InvariantCulture, out var handle))
            throw new ArgumentException("Invalid native window handle");
        var hwnd = new IntPtr(handle);
        if (hwnd == IntPtr.Zero || !IsWindow(hwnd))
            throw new ArgumentException("A live Beacon window is required for OpenGL context creation");

        EnsureOpenGlLoaded();
        var dc = GetDC(hwnd);
        if (dc == IntPtr.Zero)
            throw new InvalidOperationException($"GetDC failed ({Marshal.GetLastWin32Error()})");

        IntPtr glrc = IntPtr.Zero;
        try
        {
            var descriptor = new PixelFormatDescriptor
            {
                nSize = (ushort)Marshal.SizeOf<PixelFormatDescriptor>(),
                nVersion = 1,
                dwFlags = PfdDrawToWindow | PfdSupportOpenGl | PfdDoubleBuffer,
                iPixelType = 0, // PFD_TYPE_RGBA
                // Start with GLFW's legacy-context baseline; software WGL
                // implementations on CI often prefer 24-bit color, no depth.
                cColorBits = 24,
                cDepthBits = 0,
                iLayerType = 0 // PFD_MAIN_PLANE
            };
            var format = ChoosePixelFormat(dc, ref descriptor);
            if (format == 0 || !SetPixelFormat(dc, format, ref descriptor))
                throw new InvalidOperationException($"Failed to select an OpenGL pixel format ({Marshal.GetLastWin32Error()})");
            var activeFormat = GetPixelFormat(dc);
            var activeDescription = new PixelFormatDescriptor();
            var formats = DescribePixelFormat(dc, activeFormat, (uint)Marshal.SizeOf<PixelFormatDescriptor>(), ref activeDescription);
            glrc = wglCreateContext(dc);
            if (glrc == IntPtr.Zero)
                throw new InvalidOperationException(
                    $"Failed to create a WGL context ({Marshal.GetLastWin32Error()}); " +
                    $"requested={format}, active={activeFormat}, count={formats}, " +
                    $"flags=0x{activeDescription.dwFlags:X}, rgba={activeDescription.iPixelType}, " +
                    $"colorBits={activeDescription.cColorBits}, depthBits={activeDescription.cDepthBits}");
            if (!wglMakeCurrent(dc, glrc))
                throw new InvalidOperationException($"wglMakeCurrent failed ({Marshal.GetLastWin32Error()})");

            var version = Marshal.PtrToStringAnsi(GlGetString(GlVersion)) ?? "unknown";
            var id = NextId++;
            var context = new Context
            {
                Id = id, Window = hwnd, Dc = dc, Glrc = glrc,
                OwnerThread = Environment.CurrentManagedThreadId, Version = version
            };
            Contexts.Add(id, context);
            if (GetClientRect(hwnd, out var bounds))
                GlViewport(0, 0, Math.Max(1, bounds.right - bounds.left),
                    Math.Max(1, bounds.bottom - bounds.top));
            return new { id, version };
        }
        catch
        {
            if (glrc != IntPtr.Zero)
            {
                wglMakeCurrent(IntPtr.Zero, IntPtr.Zero);
                wglDeleteContext(glrc);
            }
            ReleaseDC(hwnd, dc);
            throw;
        }
    }

    private static object Destroy(JsonElement request)
    {
        var id = Integer(request, "id");
        if (!Contexts.TryGetValue(id, out var state))
            throw new InvalidOperationException($"OpenGL context {id} has already been destroyed");
        if (state.OwnerThread != Environment.CurrentManagedThreadId)
            throw new InvalidOperationException("OpenGL context must be destroyed on its owner thread");

        // The window may already be gone after a WM_CLOSE event; teardown
        // must still be possible and must not try to rebind a dead HWND.
        wglMakeCurrent(IntPtr.Zero, IntPtr.Zero);
        if (!wglDeleteContext(state.Glrc))
            throw new InvalidOperationException($"Failed to release WGL context ({Marshal.GetLastWin32Error()})");
        if (IsWindow(state.Window))
            ReleaseDC(state.Window, state.Dc);
        Contexts.Remove(id);
        return new { ok = true };
    }

    private static object ClearColor(JsonElement request)
    {
        Current(request);
        GlClearColor((float)Number(request, "red"), (float)Number(request, "green"),
            (float)Number(request, "blue"), (float)Number(request, "alpha"));
        return new { ok = true };
    }

    private static object Clear(JsonElement request)
    {
        Current(request);
        // The first bridge supports a color-buffer clear only. Later versions
        // can expose additional flags as typed constants.
        GlClear(GlColorBufferBit);
        return new { ok = true };
    }

    private static object Viewport(JsonElement request)
    {
        Current(request);
        var x = Integer(request, "x");
        var y = Integer(request, "y");
        var width = Integer(request, "width");
        var height = Integer(request, "height");
        if (width <= 0 || height <= 0)
            throw new ArgumentException("OpenGL viewport dimensions must be positive");
        GlViewport(x, y, width, height);
        return new { ok = true };
    }

    private static object Triangle(JsonElement request)
    {
        Current(request);
        // This initial proof uses OpenGL 1.1 compatibility functions so it
        // works even on Windows CI software drivers with no modern GL context.
        GlBegin(GlTriangles);
        GlColor3f(1, 0.22f, 0.14f);
        GlVertex2f(-0.72f, -0.68f);
        GlColor3f(0.18f, 0.9f, 0.48f);
        GlVertex2f(0.72f, -0.68f);
        GlColor3f(0.23f, 0.48f, 1);
        GlVertex2f(0, 0.72f);
        GlEnd();
        GlFlush();
        return new { ok = true };
    }


    // A small, fixed 5x7 bitmap alphabet used for debug HUDs and simple games.
    // The font is embedded as geometry: no GDI/third-party rendering dependency.
    private static readonly Dictionary<char, string[]> Glyphs = new()
    {
        ['A'] = new[] {"01110","10001","10001","11111","10001","10001","10001"},
        ['B'] = new[] {"11110","10001","10001","11110","10001","10001","11110"},
        ['C'] = new[] {"01111","10000","10000","10000","10000","10000","01111"},
        ['D'] = new[] {"11110","10001","10001","10001","10001","10001","11110"},
        ['E'] = new[] {"11111","10000","10000","11110","10000","10000","11111"},
        ['F'] = new[] {"11111","10000","10000","11110","10000","10000","10000"},
        ['G'] = new[] {"01111","10000","10000","10111","10001","10001","01111"},
        ['H'] = new[] {"10001","10001","10001","11111","10001","10001","10001"},
        ['I'] = new[] {"11111","00100","00100","00100","00100","00100","11111"},
        ['J'] = new[] {"00111","00010","00010","00010","10010","10010","01100"},
        ['K'] = new[] {"10001","10010","10100","11000","10100","10010","10001"},
        ['L'] = new[] {"10000","10000","10000","10000","10000","10000","11111"},
        ['M'] = new[] {"10001","11011","10101","10101","10001","10001","10001"},
        ['N'] = new[] {"10001","11001","10101","10011","10001","10001","10001"},
        ['O'] = new[] {"01110","10001","10001","10001","10001","10001","01110"},
        ['P'] = new[] {"11110","10001","10001","11110","10000","10000","10000"},
        ['Q'] = new[] {"01110","10001","10001","10001","10101","10010","01101"},
        ['R'] = new[] {"11110","10001","10001","11110","10100","10010","10001"},
        ['S'] = new[] {"01111","10000","10000","01110","00001","00001","11110"},
        ['T'] = new[] {"11111","00100","00100","00100","00100","00100","00100"},
        ['U'] = new[] {"10001","10001","10001","10001","10001","10001","01110"},
        ['V'] = new[] {"10001","10001","10001","10001","10001","01010","00100"},
        ['W'] = new[] {"10001","10001","10001","10101","10101","10101","01010"},
        ['X'] = new[] {"10001","10001","01010","00100","01010","10001","10001"},
        ['Y'] = new[] {"10001","10001","01010","00100","00100","00100","00100"},
        ['Z'] = new[] {"11111","00001","00010","00100","01000","10000","11111"},
        ['0'] = new[] {"01110","10011","10101","10101","11001","10001","01110"},
        ['1'] = new[] {"00100","01100","00100","00100","00100","00100","01110"},
        ['2'] = new[] {"01110","10001","00001","00010","00100","01000","11111"},
        ['3'] = new[] {"11110","00001","00001","01110","00001","00001","11110"},
        ['4'] = new[] {"00010","00110","01010","10010","11111","00010","00010"},
        ['5'] = new[] {"11111","10000","10000","11110","00001","00001","11110"},
        ['6'] = new[] {"01110","10000","10000","11110","10001","10001","01110"},
        ['7'] = new[] {"11111","00001","00010","00100","01000","01000","01000"},
        ['8'] = new[] {"01110","10001","10001","01110","10001","10001","01110"},
        ['9'] = new[] {"01110","10001","10001","01111","00001","00001","01110"},
        [':'] = new[] {"00000","00100","00100","00000","00100","00100","00000"},
        ['/'] = new[] {"00001","00001","00010","00100","01000","10000","10000"},
        ['-'] = new[] {"00000","00000","00000","11111","00000","00000","00000"},
        ['!'] = new[] {"00100","00100","00100","00100","00100","00000","00100"},
        ['.'] = new[] {"00000","00000","00000","00000","00000","00100","00100"},
        ['+'] = new[] {"00000","00100","00100","11111","00100","00100","00000"},
        ['?'] = new[] {"01110","10001","00001","00010","00100","00000","00100"},
    };

    private static float Color(JsonElement element, string key)
    {
        var n = Number(element, key);
        if (n < 0 || n > 1) throw new ArgumentException($"{key} must be between 0 and 1");
        return (float)n;
    }

    private static void Quad(double x, double y, double width, double height)
    {
        GlVertex2f((float)x, (float)y);
        GlVertex2f((float)(x + width), (float)y);
        GlVertex2f((float)(x + width), (float)(y + height));
        GlVertex2f((float)x, (float)(y + height));
    }

    // Window wake uses the host's existing event pump. It does no work on the
    // background thread except enqueue an ordinary Win32 message. Chess
    // search, controls and all application state remain entirely in Beacon.
    private static object Wake(JsonElement request)
    {
        var context = Current(request);
        var milliseconds = Integer(request, "milliseconds");
        if (milliseconds < 0 || milliseconds > 30000)
            throw new ArgumentOutOfRangeException(nameof(milliseconds));
        var token = Integer(request, "token");
        if (token < 1 || token > 32000)
            throw new ArgumentOutOfRangeException(nameof(token));
        var hwnd = context.Window;
        _ = Task.Delay(milliseconds).ContinueWith(_ =>
        {
            if (IsWindow(hwnd))
            {
                var position = new IntPtr((token << 16) | WakeMarkerX);
                PostMessage(hwnd, WmMouseMove, IntPtr.Zero, position);
            }
        });
        return new { ok = true };
    }

    // Ear-clip simple, possibly concave polygons into triangles. Crown points
    // and horse silhouettes are concave: a raw triangle fan fills them badly.
    // This is generic rendering infrastructure, independent of chess.
    private static float Cross((float X, float Y) a, (float X, float Y) b,
                               (float X, float Y) c) =>
        (b.X - a.X) * (c.Y - a.Y) - (b.Y - a.Y) * (c.X - a.X);

    private static void FillPolygon(JsonElement jsonPoints)
    {
        var points = new List<(float X, float Y)>();
        foreach (var point in jsonPoints.EnumerateArray())
            points.Add(((float)Number(point, "x"), (float)Number(point, "y")));

        float area = 0;
        for (var i = 0; i < points.Count; i++)
        {
            var a = points[i];
            var b = points[(i + 1) % points.Count];
            area += a.X * b.Y - b.X * a.Y;
        }
        if (Math.Abs(area) < 0.0001f)
            throw new ArgumentException("Polygon has zero area");

        var winding = area >= 0 ? 1 : -1;
        var remaining = new List<int>();
        for (var i = 0; i < points.Count; i++) remaining.Add(i);

        while (remaining.Count > 2)
        {
            var clipped = false;
            for (var i = 0; i < remaining.Count; i++)
            {
                var pa = remaining[(i + remaining.Count - 1) % remaining.Count];
                var pb = remaining[i];
                var pc = remaining[(i + 1) % remaining.Count];
                var a = points[pa];
                var b = points[pb];
                var c = points[pc];
                if (winding * Cross(a, b, c) <= 0.0001f) continue;

                var occupied = false;
                foreach (var other in remaining)
                {
                    if (other == pa || other == pb || other == pc) continue;
                    var p = points[other];
                    if (winding * Cross(a, b, p) >= -0.0001f &&
                        winding * Cross(b, c, p) >= -0.0001f &&
                        winding * Cross(c, a, p) >= -0.0001f)
                    {
                        occupied = true;
                        break;
                    }
                }
                if (occupied) continue;

                GlVertex2f(a.X, a.Y);
                GlVertex2f(b.X, b.Y);
                GlVertex2f(c.X, c.Y);
                remaining.RemoveAt(i);
                clipped = true;
                break;
            }
            if (!clipped)
                throw new ArgumentException("Polygon is self-intersecting or degenerate");
        }
    }

    private static object Batch(JsonElement request)
    {
        Current(request);
        var width = Integer(request, "width");
        var height = Integer(request, "height");
        if (width <= 0 || height <= 0)
            throw new ArgumentException("Frame dimensions must be positive");
        var commands = request.GetProperty("commands");
        if (commands.ValueKind != JsonValueKind.Array || commands.GetArrayLength() > 20000)
            throw new ArgumentException("A batch requires an array of at most 20000 commands");
        GlViewport(0, 0, width, height);
        GlMatrixMode(GlProjection);
        GlLoadIdentity();
        GlOrtho(0, width, height, 0, -1, 1);
        GlMatrixMode(GlModelview);
        GlLoadIdentity();
        GlBegin(GlQuads);
        try
        {
            foreach (var command in commands.EnumerateArray())
            {
                var kind = String(command, "kind");
                GlColor3f(Color(command, "red"), Color(command, "green"), Color(command, "blue"));
                var x = Number(command, "x");
                var y = Number(command, "y");
                if (kind == "rect")
                {
                    var w = Number(command, "width");
                    var h = Number(command, "height");
                    if (w <= 0 || h <= 0) throw new ArgumentException("Rectangle dimensions must be positive");
                    Quad(x, y, w, h);
                }
                else if (kind == "text")
                {
                    var value = String(command, "text").ToUpperInvariant();
                    var scale = Number(command, "scale");
                    if (scale < 1 || scale > 12 || value.Length > 256)
                        throw new ArgumentException("Bitmap text requires scale 1..12 and at most 256 characters");
                    for (var i = 0; i < value.Length; i++)
                    {
                        if (!Glyphs.TryGetValue(value[i], out var glyph)) continue;
                        for (var row = 0; row < glyph.Length; row++)
                            for (var col = 0; col < glyph[row].Length; col++)
                                if (glyph[row][col] == '1')
                                    Quad(x + i * 6 * scale + col * scale,
                                         y + row * scale, scale, scale);
                    }
                }
                else if (kind == "ellipse")
                {
                    var rx = Number(command, "rx");
                    var ry = Number(command, "ry");
                    if (rx <= 0 || ry <= 0 || rx > 4096 || ry > 4096)
                        throw new ArgumentException("Ellipse radii must be positive and bounded");
                    GlEnd();
                    GlBegin(GlTriangleFan);
                    GlVertex2f((float)x, (float)y);
                    for (var n = 0; n <= 40; n++)
                    {
                        var a = n * Math.PI * 2 / 40;
                        GlVertex2f((float)(x + Math.Cos(a) * rx), (float)(y + Math.Sin(a) * ry));
                    }
                    GlEnd();
                    GlBegin(GlQuads);
                }
                else if (kind == "polygon")
                {
                    var points = command.GetProperty("points");
                    if (points.ValueKind != JsonValueKind.Array ||
                        points.GetArrayLength() < 3 || points.GetArrayLength() > 64)
                        throw new ArgumentException("Polygon requires 3..64 vertices");
                    GlEnd();
                    GlBegin(GlTriangles);
                    try { FillPolygon(points); }
                    finally { GlEnd(); }
                    GlBegin(GlQuads);
                }
                else throw new ArgumentException($"Unsupported graphics command: {kind}");
            }
        }
        finally { GlEnd(); }
        GlFlush();
        return new { ok = true };
    }

    private static object Present(JsonElement request)
    {
        var state = Current(request);
        if (!SwapBuffers(state.Dc))
            throw new InvalidOperationException($"SwapBuffers failed ({Marshal.GetLastWin32Error()})");
        return new { ok = true };
    }

    private static object SamplePixel(JsonElement request)
    {
        Current(request);
        var x = Integer(request, "x");
        var y = Integer(request, "y");
        var pixel = new byte[4];
        var memory = GCHandle.Alloc(pixel, GCHandleType.Pinned);
        try
        {
            GlReadPixels(x, y, 1, 1, GlRgba, GlUnsignedByte, memory.AddrOfPinnedObject());
        }
        finally { memory.Free(); }
        return new
        {
            red = (double)pixel[0] / 255,
            green = (double)pixel[1] / 255,
            blue = (double)pixel[2] / 255,
            alpha = (double)pixel[3] / 255
        };
    }
}
