---
title: std.inspect
---

`std.inspect` connects Beacon programs to an opted-in running Beacon process. It exposes read-only snapshots of Beacon's own values without using CLR debugger APIs.

## Try the live Inspector

On Windows, run the application shell from the repository root:

```bash
./beacon.sh examples/inspector-ui.beacon
```

Click **Launch sample**. The Inspector starts `examples/inspector-target.beacon` in a second process with inspection enabled. Click **Increment** in the counter app, then **Refresh** in the Inspector to observe the value change. You can also attach using the PID of another Beacon process started in inspection mode.

Start a target independently:

```bash
./beacon.sh inspect examples/inspector-target.beacon
```

Only programs started with `--inspect` expose an inspection endpoint.

## API

```beacon
include std.inspect

pid: number = inspect.launch("examples/inspector-target.beacon")
state: record = inspect.connect(pid)

if state.connected then
    print(state.source)
    for [i: number = 0, i < state.values.length(), i += 1]
        print(state.values@i.name)
    loop
end
```

- `inspect.launch(path)` starts an inspection-enabled Beacon process and returns its PID.
- `inspect.connect(pid)` requests an initial snapshot from a known PID.
- `inspect.snapshot(pid)` requests another snapshot.

The resulting Record contains `protocol`, `connected`, `status`, `source`, and `values` for a connected target. When disconnected, `connected` is false and `error` explains the failure.

Each value is a Record with `name`, `kind`, `preview`, `children`, and `truncated`. Nested Lists and Records are bounded to four levels and 64 entries per container, with cycle detection. Functions remain opaque; inspection never executes them.

## Safety and scope

The transport is a **same-user local named pipe** with one read-only snapshot command. There is no network listener, expression evaluator, or arbitrary runtime command. This is a developer diagnostic surface; inspectable values may include sensitive application state and should not be enabled in untrusted environments.

Snapshots are requested manually in v1. An inspected app continues independently of the Inspector and remains usable after the Inspector disconnects. The Inspector currently renders nested values as an expanded or collapsed text tree; per-node lazy expansion, continuous updates, breakpoints, and call-stack inspection are future milestones.

`std.inspect` can make local inspection requests on any supported CLR platform. The GUI Inspector and counter demonstration currently require the Windows backend provided by `std.window`.
