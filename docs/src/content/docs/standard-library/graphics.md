---
title: std.graphics / std.graphics.gl
description: Native graphics contexts and OpenGL in Beacon.
---

Beacon graphics APIs live under **`std.graphics`**. OpenGL-specific operations live in the nested **`std.graphics.gl`** module. The first backend uses our own independent WGL and `opengl32.dll` binding assembly; there is no Silk.NET or OpenTK dependency.

## Draw a triangle

On Windows:

```powershell
./beacon.ps1 examples/graphics-triangle.beacon
```

This displays a colored triangle in a native Beacon window. Close the window to stop.

## Use the API

```beacon
include std.window
include std.graphics
include std.graphics.gl

app: record = window.create({
    title: "Beacon OpenGL"
    width: 840
    height: 640
})

context: record = graphics.createContext(app, {
    renderer: graphics.renderer.opengl
})

window.show(app)
graphics.gl.clearColor(context, 0.06, 0.08, 0.13, 1.0)
graphics.gl.clear(context, graphics.gl.buffer.color)
graphics.gl.drawLegacyTriangle(context)
graphics.present(context)

// Close or process native events as appropriate for the application.
graphics.destroyContext(context)
window.close(app)
```

`graphics.renderer.opengl` is a standard-library descriptor. The programmer never supplies the backend as a magic string. GL buffer options similarly use `graphics.gl.buffer.color`.

## Operations

| Module | API | Purpose |
| --- | --- | --- |
| `std.graphics` | `renderer.opengl` | Named renderer descriptor |
| `std.graphics` | `available()` | Check native-window platform support |
| `std.graphics` | `createContext(app, options)` | Establish WGL context for Beacon window |
| `std.graphics` | `present(context)` | Swap buffers |
| `std.graphics` | `destroyContext(context)` | Release WGL context |
| `std.graphics.gl` | `clearColor(context, r, g, b, a)` | Set clear color |
| `std.graphics.gl` | `clear(context, buffer.color)` | Clear framebuffer |
| `std.graphics.gl` | `viewport(context, x, y, width, height)` | Set viewport |
| `std.graphics.gl` | `drawLegacyTriangle(context)` | Temporary proof-of-rendering operation |
| `std.graphics.gl` | `samplePixel(context, x, y)` | Read normalized RGBA framebuffer values |

The context holds an opaque numeric ID, the chosen renderer descriptor, and the reported GL version. Actual native handles are private to the standard-library/native boundary.

## Important limits

The first implementation uses **OpenGL 1.1 compatibility** functions so it can be tested against software-only Windows drivers. It is a real OpenGL binding, but does **not** yet expose modern core-profile shaders, vertex buffers, textures, or continuous rendering. The availability check means the Windows window backend exists; driver/context creation can still fail. Hardware acceleration depends on the installed driver.

GL contexts are thread-owned. Calls and destruction must occur on the creating thread. Windows is the first supported graphics platform. Linux/macOS backends and modern OpenGL function loading will be separate work.

Read [Native extensions](../../concepts/native-extensions/) for the ABI, trust, and dependency policy.
