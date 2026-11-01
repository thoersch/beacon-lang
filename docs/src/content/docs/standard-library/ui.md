---
title: std.ui
---

`std.ui` is Beacon's structural desktop UI layer. UI is ordinary Beacon data: Records describe elements, Lists describe children, and functions provide callbacks.

The initial scope is deliberately driven by the Beacon Inspector rather than by trying to wrap an entire native GUI framework.

```beacon
include std.window
include std.ui

app: record = window.create({
    title: "Beacon Inspector"
    width: 1180
    height: 760
})

view: record = ui.column([
    ui.heading("Beacon Inspector"),
    ui.text("Inspect Beacon source and compiler output."),
    ui.row([
        ui.button("Open", fn() = print("open")),
        ui.button("Refresh", fn() = print("refresh"))
    ])
])

ui.mount(app, view)
window.show(app)
ui.run(app)
```

## Structural UI

Constructors return Records rather than native control objects. For example, a text element is structurally equivalent to data shaped like:

```beacon
{
    kind: "text"
    text: "Ready"
}
```

This keeps Beacon's UI vocabulary independent from the Win32 implementation used by the first backend.

## Elements

The first Inspector-driven surface includes:

```beacon
ui.text("Ready")
ui.heading("Source")
ui.button("Open", onOpen)
ui.input("Search", onSearch)
ui.textArea("source text", 240)
ui.spacer(12)
```

Layout/container elements:

```beacon
ui.row([...])
ui.column([...])
ui.panel([...])
```

## Mounting

```beacon
ui.mount(app, view)
```

`mount` measures and lays out the structural tree in Beacon, lowers it to the small native-control boundary, and registers callbacks.

Rows divide their available width across their children. Columns stack children vertically. Panels provide inset content and a visual grouping boundary.

The current layout is intentionally simple. The Inspector application will drive future requirements such as richer sizing, scrolling, tree views, tables, split panes, or selection models.

## Events and callbacks

Buttons accept zero-argument callbacks:

```beacon
open: fn() = print("open")
control: record = ui.button("Open", open)
```

Inputs accept a String callback:

```beacon
searchChanged: fn(value: string) =
    print(value)

control: record = ui.input("Search", searchChanged)
```

`ui.run(app)` consumes native window events and routes UI actions back to the Beacon callbacks registered during `mount`.

When the window is resized, `std.ui` re-lays out and remounts the current structural tree.

## Design boundary

Beacon owns:

- the UI tree
- layout
- callback registration and routing
- application-level UI event handling

Stage-0 owns only the irreducible OS bridge needed to create a native window, native controls, and native events.

`std.ui` is therefore not a WinForms, WPF, or Win32 API wrapper. Its public model is Beacon's own structural vocabulary.
