---
title: std.window
---

`std.window` is Beacon's native application-window boundary. It owns window lifecycle and native input events while keeping higher-level UI composition in Beacon.

```beacon
include std.window

if window.available() then
    app: record = window.create({
        title: "Beacon Inspector"
        width: 1180
        height: 760
    })

    window.show(app)
    window.run(app, fn(event: record) =
        print(event.type)
    )
end
```

## Availability

The first backend is native Win32.

```beacon
window.available()
window.platform()
```

`available()` returns whether the current runtime can create Beacon windows. `platform()` currently returns `"windows"` when the Win32 backend is available and `"unsupported"` otherwise.

The runtime itself remains portable. A Beacon program can check availability before attempting to create a window.

## Creating a window

```beacon
app: record = window.create({
    title: "Inspector"
    width: 1000
    height: 700
})
```

The returned Record contains the native window id plus the current title, width, and height.

`title`, `width`, and `height` are optional. Width and height must be positive.

On Windows, Beacon applies its native desktop visual defaults automatically: dark title-bar integration, matching caption and border colors, and rounded system corners where the OS supports them. Applications do not need to configure raw Win32 appearance flags.

## Lifecycle

```beacon
window.show(app)
window.close(app)
```

For applications that want direct control of native events:

```beacon
window.run(app, fn(event: record) = [
    if event.type == "keyDown" then
        print(event.key)
    end,
    null
])
```

Or read one event at a time:

```beacon
event: record = window.nextEvent(app)
```

The initial native event vocabulary includes:

- `close`
- `resize` with `width` and `height`
- `keyDown` and `keyUp` with `key`
- `mouseMove`, `mouseDown`, and `mouseUp` with `x` and `y`
- UI-generated `action` and `input` events used by `std.ui`

## Runtime boundary

The Stage-0 runtime exposes one internal structured primitive for native desktop operations. `std.window` turns that primitive into Beacon-facing lifecycle and event behavior.

The native backend owns only irreducible platform rendering and event plumbing. Beacon's UI tree, semantic visual roles, layout, spacing, and callback routing remain in `std.ui`.
