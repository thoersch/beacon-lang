---
title: GitHub language recognition
description: Beacon syntax highlighting, GitHub Linguist, and repository language statistics.
---

Beacon source files use the `.beacon` extension. The repository ships a [TextMate grammar](https://github.com/thoersch/beacon-lang/blob/master/editors/vscode/syntaxes/beacon.tmLanguage.json) that is shared by the VS Code extension and the documentation site.

## Highlighting today

**VS Code:** Install the [Beacon extension](../../getting-started/vscode/) to highlight `.beacon` files.

**Documentation site:** Beacon examples on this site use fenced `beacon` code blocks rendered with the same grammar through Shiki.

**GitHub.com:** Native coloring of `.beacon` files, highlighting of `beacon` fenced code blocks, and inclusion of Beacon in the repository's **Languages** percentages depend on GitHub's central [Linguist](https://github.com/github-linguist/linguist) registry.

## Why a repository setting isn't enough

As of November 2026, Linguist does not include a `Beacon` language definition. A `.gitattributes` file can override classification to a *known* language, but cannot define a new language or its highlighting rules.

Beacon includes this forward-looking entry in `.gitattributes`:

```gitattributes
*.beacon linguist-language=Beacon linguist-detectable
```

This makes classification intent explicit, but **does not make Beacon appear in GitHub's Languages bar today**. We do not relabel Beacon source as a different programming language.

## Path to official support

GitHub Linguist's [contribution requirements](https://github.com/github-linguist/linguist/blob/main/CONTRIBUTING.md#adding-a-language) include:

1. A new entry in `languages.yml`, with language metadata and extension
2. An appropriately licensed TextMate grammar
3. Representative samples of real Beacon source
4. A unique language ID generated through Linguist's tooling
5. Evidence of broad public use across repositories

Linguist requires substantial independent adoption for new languages (see its [usage thresholds](https://github.com/github-linguist/linguist/blob/main/CONTRIBUTING.md#language-extension-and-filename-usage-requirements)). A single repository cannot satisfy that requirement by itself.

Once GitHub accepts and deploys a Beacon definition, native file and fenced-code highlighting and language percentages can recognize Beacon directly.

## How to help

Using Beacon in public repositories and sharing representative real-world programs provides the best foundation for eventual recognition. Grammar improvements belong in [Beacon issues](https://github.com/thoersch/beacon-lang/issues).

Until GitHub supports it natively, the documentation site and VS Code remain Beacon's supported highlighted representations.
