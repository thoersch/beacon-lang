# Beacon Language for VS Code

Initial VS Code language support for Beacon.

## Features

- `.beacon` file association
- Syntax highlighting
- `//` comments
- Bracket matching and auto-closing
- Basic indentation support
- Highlighting for:
  - control flow
  - functions and types
  - explicit type annotations and unions
  - local and `std.*` includes
  - strings and interpolation
  - numbers and constants
  - operators
  - member access and implicit receiver syntax

## Development

Open this directory in VS Code:

```bash
code editors/vscode
```

Then press `F5` to launch an Extension Development Host.

Open any `.beacon` file in the development host to test the grammar.
