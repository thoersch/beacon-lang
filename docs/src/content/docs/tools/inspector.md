---
title: Live Inspector
description: Run Beacon Inspector and observe the live state of another Beacon application.
---

Beacon Inspector is a desktop developer tool **written in Beacon**. It connects to an explicitly inspection-enabled Beacon process and displays the application's source and top-level runtime values.

The initial native GUI backend is Windows. The inspection protocol is local and read-only.

## Run the Inspector

From the repository root on Windows, open PowerShell:

```powershell
./beacon.ps1 examples/inspector-ui.beacon
```

In the Inspector:

1. Choose **Launch sample**. This starts a separate Beacon Counter window with inspection enabled.
2. Observe the source and the initial `counter: number = 0` in the Inspector.
3. Click **Increment** in the Counter window.
4. Return to the Inspector and click **Refresh**. The live counter now reads `1`.
5. Close the Counter window; the next refresh reports a disconnected session.

## Attach to a running program

Start the demonstration target with inspection enabled:

```powershell
./beacon.ps1 inspect examples/inspector-target.beacon
```

Enter that process's PID in the Inspector's attach field and select **Attach**.

Only applications explicitly started in inspection mode expose an endpoint. Attaching to an arbitrary CLR process is outside the current tool's scope.

## Inspection API

Programmatic clients can use `std.inspect`:

```beacon
include std.inspect

pid: number = inspect.launch("examples/inspector-target.beacon")
snapshot: record = inspect.connect(pid)

if snapshot.connected then
    print(snapshot.source)
    print(snapshot.values.length())
end
```

| Function | Purpose |
| --- | --- |
| `inspect.launch(path)` | Start a Beacon application with inspection enabled; return its PID |
| `inspect.connect(pid)` | Connect and read an initial snapshot |
| `inspect.snapshot(pid)` | Request a new snapshot |

Each value has a `name`, `kind`, `preview`, `children`, and `truncated` field. The current renderer shows nested data as a formatted tree, with a global expand/collapse control.

## Security and operational boundaries

- **Opt-in:** inspection is disabled for normal app launches
- **Local:** the agent uses a same-user named pipe, not a network service
- **Read-only:** no evaluation, mutation, or remote execution commands
- **Bounded:** nested values have depth/size limits and cycle detection
- **Manual refresh:** v1 snapshots are requested rather than continuously streamed

An inspection snapshot can expose sensitive values. Enable this feature only in a trusted development environment.

## What's next

The current milestone proves the path between a running Beacon runtime, the transport, and another Beacon application's UI. Future improvements include incremental reconciliation, automatic updates, lazy per-node expansion, and source navigation. Breakpoints, stepping, and call stacks remain future debugger features.

See [`std.inspect`](../../standard-library/inspect/) for API details and [`std.ui`](../../standard-library/ui/) for the structural UI model.
