---
title: Native extensions
description: Load trusted platform extensions independently of Beacon's frozen bootstrap.
---

Beacon has a new **generic extension boundary**, designed so application libraries can evolve without embedding feature-specific bindings in the frozen Stage-0 runtime.

```text
Beacon application
     ↓
std.graphics / std.graphics.gl       Beacon modules
     ↓
hostNative(module, request)          Generic extension ABI v1
     ↓
native/opengl/Beacon.Native.opengl.dll
     ↓
Windows WGL / opengl32.dll           OS graphics driver
```

The compiler remains self-hosted. The seed gains **one** general intrinsic, `hostNative`, and a generic native-window handle accessor; it does not contain OpenGL functions, Silk.NET, OpenTK, or any graphics-specific dependency.

## Contract: ABI v1

The intrinsic accepts a lowercase module identifier and a Beacon Record. It locates a trusted local assembly:

```text
native/<module>/Beacon.Native.<module>.dll
```

The assembly exposes a public static `Beacon.Native.Extension` type with:

- `AbiVersion` — public static integer property equal to `1`
- `Invoke(string json)` — public static method returning JSON text

The runtime converts Beacon Atom/List/Record data to JSON, passes it to the extension, and turns the result back into Beacon values. The request and response are each limited to 4 MiB. The module resolver only searches within the configured `BEACON_HOME/native/` directory, never an arbitrary user-provided absolute path.

The extension is cached once loaded. Errors are surfaced to Beacon callers.

## Security model

**Native extensions are trusted in-process assemblies, not sandboxes.** Loading one grants it the application process's privileges. Install or build only extensions you trust. The JSON ABI prevents accidental coupling to Beacon's environment objects or Core representation; it is not a security isolation boundary.

## Independent OpenGL bindings

The first extension is [`native/opengl`](https://github.com/thoersch/beacon-lang/tree/master/native/opengl): an explicit P/Invoke mapping to Windows WGL and OpenGL 1.1, built with the standard .NET SDK and **no external graphics packages**. The source and frozen compiled module are versioned independently of Stage-0.

A modern rendering backend will need context-aware WGL function loading, shaders, VAOs/VBOs, efficient packed buffers, and graphics resource ownership. The current JSON ABI prioritizes correctness and portability of the interop contract; it is not suitable for high-volume vertex uploads.

The longer-term goal is a truly independent application runtime and a reusable native extension system that can also support audio, SQLite, compression, and other integrations.
