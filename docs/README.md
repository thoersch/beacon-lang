# Beacon documentation

The Beacon documentation site is built with [Astro Starlight](https://starlight.astro.build/) and published through GitHub Pages.

## Local development

From this directory:

```bash
npm install
npm run dev
```

Astro will print the local preview URL.

Build the production site with:

```bash
npm run build
```

The generated site is written to `dist/`.

## Content

Documentation pages live under:

```text
src/content/docs/
```

Beacon code blocks use the same TextMate grammar as the repository's VS Code extension:

```text
../editors/vscode/syntaxes/beacon.tmLanguage.json
```

## Publishing

`.github/workflows/docs.yml` validates documentation changes on pull requests and publishes the production build to GitHub Pages after changes reach `master`.

For the first deployment, configure the repository's **Settings → Pages → Build and deployment → Source** to **GitHub Actions**.
