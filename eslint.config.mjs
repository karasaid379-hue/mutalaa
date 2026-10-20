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
      'no-restricted-syntax': [
        'error',
        {
          selector:
            'CallExpression[callee.property.name=/^toLocale(Upper|Lower)Case$/][arguments.length=0]',
          message:
            'Yerel ayari acikca verin ya da packages/search icindeki kultursuz esleme kullanin.',
        },
        {
          selector: "CallExpression[callee.property.name='localeCompare'][arguments.length<2]",
          message:
            "Turkce siralama icin Intl.Collator('tr'), diger durumlarda sirali karsilastirma kullanin.",
        },
      ],
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

export default defineConfig([...baseConfig, prettier]);
