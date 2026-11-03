---
title: std.ui
---

`std.ui` is Beacon's structural desktop UI layer. UI is ordinary Beacon data: Records describe elements, Lists describe children, and functions provide callbacks.

The library ships with a polished opinionated desktop visual system by default. Applications should look intentional without every project rebuilding typography, spacing, colors, button hierarchy, and editor styling from scratch.

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
    ui.muted("Source, Core, and CLR inspection for the Beacon toolchain."),
    ui.row([
        ui.primaryButton("Open source", onOpen),
        ui.button("Refresh", onRefresh)
    ]),
    ui.panel([
        ui.heading("Source"),
        ui.input("Search source", onSearch),
        ui.code(source, 260)
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

## Default visual system

The initial native implementation uses a dark, developer-tool-oriented visual system with:

- dark window chrome and rounded system corners where Windows supports them
- Segoe UI typography for interface text
- a monospaced code role for source and generated output
- primary and secondary button hierarchy
- muted supporting text
- dark editor/input surfaces
- consistent panel surfaces and borders
- larger outer margins, panel padding, and vertical rhythm

The default is deliberate. Beacon applications should start from a coherent visual language rather than raw platform defaults. Custom theming can be added later when a real application requires it.

## Elements

Text and hierarchy:

```beacon
ui.heading("Source")
ui.text("Ready")
ui.muted("Compiled 2 seconds ago")
```

Actions:

```beacon
ui.primaryButton("Run", onRun)
ui.button("Refresh", onRefresh)
```

Inputs and editors:

```beacon
ui.input("Search source", onSearch)
ui.textArea("Editable notes", 180)
ui.code("name: string = \"Ada\"", 260)
```

`input` uses its String argument as placeholder text. `code` is a read-only monospaced surface intended for source, Core, plans, logs, and similar developer-facing content.

Layout/container elements:

```beacon
ui.row([...])
ui.column([...])
ui.panel([...])
ui.spacer(12)
```

## Layout behavior

`ui.mount(app, view)` measures and lays out the structural tree in Beacon, lowers it to the small native-control boundary, and registers callbacks.

Columns stack children vertically with consistent spacing. Panels provide padded elevated surfaces. Rows use intrinsic widths for controls such as buttons and distribute remaining width to flexible children such as inputs and containers. This avoids the stretched stock-control appearance of the first implementation.

The Inspector application continues to drive future requirements such as scrolling, split panes, trees, tables, selection models, dialogs, menus, and richer sizing constraints.

## Events and callbacks

Buttons accept zero-argument callbacks:

```beacon
open: fn() = print("open")
control: record = ui.primaryButton("Open", open)
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

- the UI tree and semantic visual roles
- layout and spacing
- control hierarchy and composition
- callback registration and routing
- application-level UI event handling

Stage-0 owns the irreducible OS bridge needed to create and render native windows and controls and to surface native events.

`std.ui` is therefore not a WinForms, WPF, or Win32 API wrapper. Its public model is Beacon's own structural vocabulary.
