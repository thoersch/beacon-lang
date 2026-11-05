using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text.Json;

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

    private static readonly Dictionary<int, Context> Contexts = new();
    private static int NextId = 1;

    private const uint PfdDrawToWindow = 0x00000004;
    private const uint PfdSupportOpenGl = 0x00000020;
    private const uint PfdDoubleBuffer = 0x00000001;
    private const uint GlColorBufferBit = 0x00004000;
    private const uint GlTriangles = 0x0004;
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
                cColorBits = 32,
                cDepthBits = 24,
                iLayerType = 0 // PFD_MAIN_PLANE
            };
            var format = ChoosePixelFormat(dc, ref descriptor);
            if (format == 0 || !SetPixelFormat(dc, format, ref descriptor))
                throw new InvalidOperationException($"Failed to select an OpenGL pixel format ({Marshal.GetLastWin32Error()})");
            glrc = wglCreateContext(dc);
            if (glrc == IntPtr.Zero || !wglMakeCurrent(dc, glrc))
                throw new InvalidOperationException($"Failed to create a WGL context ({Marshal.GetLastWin32Error()})");

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
        var state = Current(request);
        wglMakeCurrent(IntPtr.Zero, IntPtr.Zero);
        if (!wglDeleteContext(state.Glrc))
            throw new InvalidOperationException($"Failed to release WGL context ({Marshal.GetLastWin32Error()})");
        ReleaseDC(state.Window, state.Dc);
        Contexts.Remove(state.Id);
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
