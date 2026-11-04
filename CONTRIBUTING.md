# Contributing to Beacon

Thanks for helping improve Beacon. The project is experimental and evolving; small, focused changes with clear tests are the easiest to review.

For significant language or runtime changes, open an [issue](https://github.com/thoersch/beacon-lang/issues) explaining the motivation, proposed syntax or API, compatibility implications, and how the design preserves Beacon's small structural core.

## Development setup

**Requirements:** Git and .NET 8 or newer. Documentation and VS Code packaging also require Node.js.

```bash
git clone https://github.com/thoersch/beacon-lang.git
cd beacon-lang
./beacon.sh examples/hello.beacon
```

On Windows, use `./beacon.ps1` in PowerShell or `beacon.cmd` in Command Prompt.

## Verify your changes

Run the self-hosting fixed-point check before opening a PR:

```bash
./beacon.sh self-host
```

For source behavior, add a runnable `.beacon` regression example or extend the relevant `.github/workflows/` test. Compiler changes should preserve structured diagnostics, type rules, and fixed-point verification.

Documentation:

```bash
cd docs
npm install
npm run build
```

Editor grammar:

```bash
cd editors/vscode
npm install
npm run check:syntax
npm run package
```

Keep the checked-in VSIX grammar synchronized with the source grammar when changing highlighting.

## Beacon code conventions

- Prefer explicit types and small, readable functions.
- Use `when / otherwise` for meaningful multiway condition dispatch; use `if / else` for simple decisions.
- Favor named Record fields (`.`) and List-only positional indexing (`@`).
- Use module-level `fn<private>` for internal helpers. Functions are public by default.
- Keep higher-level behavior in Beacon when Beacon can express it.
- Avoid new fundamental Core forms when a construct lowers naturally to Atom, List, or Record.
- Preserve platform checks and non-Windows startup when changing native UI or host behavior.
- Avoid permanent C# compiler logic as a substitute for implementing a feature in Beacon.

## Pull requests

A good PR has a concise motivation, the exact user-visible behavior, representative Beacon syntax, and relevant tests. Changes to the runtime/bootstrap boundary should explain why a host primitive is necessary.

Use the pull request checklist to describe validation and known platform limitations. CI is the final gate; local checks reduce review time.

## Documentation and highlighting

Documentation lives in [`docs/`](docs/). Use the `beacon` fenced code-block identifier so examples receive the official grammar on the docs site.

The [VS Code extension](editors/vscode/syntaxes/beacon.tmLanguage.json) and docs share one TextMate grammar. GitHub requires upstream Linguist support before native syntax highlighting and language percentages can recognize Beacon; see the [recognition guide](https://thoersch.github.io/beacon-lang/community/language-recognition/).

## Reporting issues

Include a minimal `.beacon` reproduction, actual and expected behavior, the launch command, operating system, .NET version, and relevant diagnostics. For UI rendering issues, include a screenshot if possible.

See [compiler architecture](https://thoersch.github.io/beacon-lang/concepts/architecture/) and [runnable examples](examples/) for context.
