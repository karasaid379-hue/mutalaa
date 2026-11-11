// Root ESLint config: shared baseline plus helpers for the package configs.
//
// Why packages have their own eslint.config.mjs: path.relative() of Node on Windows lower-cases
// paths before comparing them, and the project folder contains a capital dotted I (U+0130).
// The relative path ESLint computes is then shifted by one character, so directory globs such as
// 'packages/**/*.ts' silently never match. Package configs use '**/*.ts', which is immune.
import { defineConfig } from 'eslint/config';
import tseslint from 'typescript-eslint';
import prettier from 'eslint-config-prettier';

const platformGroup = {
  group: ['react-native', 'react-native-*', 'expo', 'expo-*', 'next', 'next/*'],
  message: 'Paylasilan paketlerde react-native, expo-* ve next kullanilmaz (Proje yapisi 2).',
};

/**
 * Culture-dependent calls (Proje yapisi 5). Shared with the app configs, which add their own selectors
 * on top: a later no-restricted-syntax entry replaces this rule, so it must spread this list.
 */
export const localeRestrictedSyntax = [
  {
    selector:
      'CallExpression[callee.property.name=/^toLocale(Upper|Lower)Case$/][arguments.length=0]',
    message: 'Yerel ayari acikca verin ya da packages/search icindeki kultursuz esleme kullanin.',
  },
  {
    selector: "CallExpression[callee.property.name='localeCompare'][arguments.length<2]",
    message:
      "Turkce siralama icin Intl.Collator('tr'), diger durumlarda sirali karsilastirma kullanin.",
  },
];

/** Baseline for every workspace package (also used when ESLint runs at the repository root). */
export const baseConfig = [
  {
    ignores: [
      '**/dist/**',
      '**/.turbo/**',
      '**/.expo/**',
      'apps/mobile/android/**',
      'apps/mobile/ios/**',
      '.tmp/**',
      'data/**',
      'docs/**',
      'server/**',
      'pipeline/**',
    ],
  },
  tseslint.configs.recommended,
  {
    rules: {
      'no-restricted-syntax': ['error', ...localeRestrictedSyntax],
    },
  },
  {
    files: ['**/*.mjs'],
    languageOptions: {
      globals: { console: 'readonly', process: 'readonly' },
    },
  },
];

/**
 * Import rules for packages/* (Proje yapisi 2 ve 5): no react-native, expo-*, next.
 * With leaf = true (anchors, search) no other @mutalaa/* package may be imported either;
 * the test vector package is the one allowed workspace import (dev dependency).
 * @param {{ leaf?: boolean }} [options]
 */
export function packageImportRules({ leaf = false } = {}) {
  const patterns = leaf
    ? [
        platformGroup,
        {
          group: ['@mutalaa/*', '!@mutalaa/test-vectors'],
          message: 'anchors ve search yaprak pakettir; baska @mutalaa/* paketine baglanamaz.',
        },
      ]
    : [platformGroup];
  return [
    {
      files: ['**/*.ts'],
      rules: { 'no-restricted-imports': ['error', { patterns }] },
    },
  ];
}

/**
 * Import rules for apps (apps/editor, later apps/web): no react-native, expo-*, next, react-router-dom;
 * only the listed @mutalaa/* packages. Node modules are allowed in tests and config files only.
 * Covers .ts and .tsx files.
 * @param {{ allow?: string[] }} [options] allowed @mutalaa/* package names
 */
export function appImportRules({ allow = [] } = {}) {
  const patterns = [
    platformGroup,
    {
      group: ['@mutalaa/*', ...allow.map((name) => `!${name}`)],
      message: 'Uygulama yalniz izin verilen @mutalaa/* paketlerine baglanabilir.',
    },
    {
      group: ['react-router-dom'],
      message: "react-router-dom kullanilmaz; 'react-router' ve 'react-router/dom' kullanin.",
    },
  ];
  const nodeModules = {
    regex:
      '^(node:.+|fs|path|os|child_process|crypto|url|util|stream|buffer|http|https|net|zlib)(/.*)?$',
    message: 'Node modulleri yalniz test ve yapilandirma dosyalarinda kullanilir.',
  };
  return [
    {
      files: ['**/*.{ts,tsx}'],
      rules: { 'no-restricted-imports': ['error', { patterns }] },
    },
    {
      files: ['**/*.{ts,tsx}'],
      ignores: ['**/test/**', '**/*.test.{ts,tsx}', '**/*.config.ts'],
      rules: { 'no-restricted-imports': ['error', { patterns: [...patterns, nodeModules] }] },
    },
  ];
}

export default defineConfig([...baseConfig, prettier]);
