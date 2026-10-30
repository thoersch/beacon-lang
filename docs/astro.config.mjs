import { readFileSync } from 'node:fs';
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

const beaconGrammar = {
  ...JSON.parse(
    readFileSync(
      new URL('../editors/vscode/syntaxes/beacon.tmLanguage.json', import.meta.url),
      'utf-8',
    ),
  ),
  name: 'beacon',
  aliases: ['beacon'],
};

export default defineConfig({
  site: 'https://thoersch.github.io',
  base: '/beacon-lang',
  integrations: [
    starlight({
      title: 'Beacon',
      description:
        'Documentation for Beacon, a compiled, homoiconic-inspired, and self-hosted programming language targeting the CLR.',
      customCss: ['./src/styles/custom.css'],
      editLink: {
        baseUrl: 'https://github.com/thoersch/beacon-lang/edit/master/docs/',
      },
      social: [
        {
          icon: 'github',
          label: 'GitHub',
          href: 'https://github.com/thoersch/beacon-lang',
        },
      ],
      sidebar: [
        {
          label: 'Start here',
          items: [
            { label: 'Overview', slug: '' },
            { label: 'Installation', slug: 'getting-started/installation' },
            { label: 'VS Code', slug: 'getting-started/vscode' },
          ],
        },
        {
          label: 'Language',
          items: [{ label: 'Syntax tour', slug: 'language/syntax' }],
        },
      ],
      expressiveCode: {
        themes: ['github-dark', 'github-light'],
        shiki: {
          langs: [beaconGrammar],
        },
      },
    }),
  ],
});
