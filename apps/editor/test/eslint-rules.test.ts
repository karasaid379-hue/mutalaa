// @vitest-environment node
// Regression test of the editor's own ESLint rules (A15): the culture-dependent calls, `.normalize(`, the
// regex digit escape, constant visible text in JSX, and the import boundaries. The real editor configuration
// (apps/editor/eslint.config.mjs, which builds on the root one) lints made-up source text through the Node
// API, so a rule that stops firing (a selector typo, a later config entry that replaces the rule) turns a
// test red instead of passing unnoticed. The fake files are never written to disk.
//
// One ESLint instance is shared by all cases (loading the plugins is the slow part). The case code is built
// with `String.fromCharCode(92)` for the backslash so no escaping layer can eat it. `cwd` comes from
// `import.meta.url` and `filePath` is given explicitly; every glob in the config starts with `**/` (the
// capital dotted I in the project folder shifts the relative path of Windows Node, see the root config).
import { fileURLToPath } from 'node:url';
import { ESLint, type Linter } from 'eslint';
import { beforeAll, describe, expect, it } from 'vitest';

const BS = String.fromCharCode(92);
const editorRoot = fileURLToPath(new URL('../', import.meta.url));

let eslint: ESLint;

beforeAll(async () => {
  eslint = new ESLint({
    cwd: editorRoot,
    overrideConfigFile: fileURLToPath(new URL('../eslint.config.mjs', import.meta.url)),
  });
  // Warm-up: loads the config and the plugins once, so the cases below are quick.
  await eslint.lintText('export const warm = 1;\n', { filePath: 'src/warm-up.ts' });
}, 60_000);

async function lint(code: string, filePath: string): Promise<Linter.LintMessage[]> {
  const [result] = await eslint.lintText(`${code}\n`, { filePath });
  // A file the config ignores comes back with a warning (ruleId null): the case would test nothing.
  expect(result?.messages.some((m) => m.message.includes('ignored'))).toBe(false);
  return result?.messages ?? [];
}

/** The messages of one rule, as `ruleId: message` lines for a readable failure. */
const fired = (messages: Linter.LintMessage[], ruleId: string) =>
  messages.filter((m) => m.ruleId === ruleId).map((m) => m.message);

describe('culture and text rules (src, .ts)', () => {
  const cases: { name: string; code: string; message: RegExp }[] = [
    {
      name: '.normalize( call (K-26: no normalization on the client)',
      code: "export const f = (s: string) => s.normalize('NFC');",
      message: /normalize edilmez/,
    },
    {
      name: `regex digit escape (${BS}d)`,
      code: `export const r = /[a-z]${BS}d+/;`,
      message: /\[0-9\]/,
    },
    {
      name: 'toLocaleUpperCase() without a locale',
      code: 'export const f = (s: string) => s.toLocaleUpperCase();',
      message: /Yerel ayari/,
    },
    {
      name: 'toLocaleLowerCase() without a locale',
      code: 'export const f = (s: string) => s.toLocaleLowerCase();',
      message: /Yerel ayari/,
    },
    {
      name: 'localeCompare with one argument',
      code: 'export const f = (a: string, b: string) => a.localeCompare(b);',
      message: /Intl\.Collator/,
    },
  ];

  it.each(cases)('fires: $name', async ({ code, message }) => {
    const messages = await lint(code, 'src/zz-fake-rule.ts');
    const lines = fired(messages, 'no-restricted-syntax');
    expect(lines.length).toBe(1);
    expect(lines[0]).toMatch(message);
  });

  it('stays quiet on the allowed forms (explicit locale, [0-9], two-argument localeCompare)', async () => {
    const code = [
      "export const a = (s: string) => s.toLocaleLowerCase('tr-TR');",
      "export const b = (s: string) => s.toLocaleUpperCase('tr');",
      'export const c = /[0-9]+/;',
      "export const d = (x: string, y: string) => x.localeCompare(y, 'tr');",
    ].join('\n');
    expect(await lint(code, 'src/zz-fake-rule.ts')).toEqual([]);
  });
});

describe('visible text rules (src, .tsx)', () => {
  const cases: { name: string; code: string; message: RegExp }[] = [
    {
      name: 'constant text inside JSX',
      code: 'export function A() { return <p>Deneme</p>; }',
      message: /JSX icine sabit metin/,
    },
    {
      name: 'a string literal in a JSX expression',
      code: 'export function A() { return <p>{"Deneme"}</p>; }',
      message: /JSX icine sabit metin/,
    },
    {
      name: 'constant aria-label text',
      code: 'export function A() { return <button type="button" aria-label="Deneme" />; }',
      message: /aria-label, title, placeholder ve alt/,
    },
    {
      name: 'constant aria-label text in an expression container',
      code: 'export function A() { return <button type="button" aria-label={"Deneme"} />; }',
      message: /aria-label, title, placeholder ve alt/,
    },
  ];

  it.each(cases)('fires: $name', async ({ code, message }) => {
    const messages = await lint(code, 'src/zz-fake-rule.tsx');
    const lines = fired(messages, 'no-restricted-syntax');
    expect(lines.length).toBe(1);
    expect(lines[0]).toMatch(message);
  });

  it('applies the culture rules in .tsx files too', async () => {
    const messages = await lint(
      "export const f = (s: string) => s.normalize('NFC');",
      'src/zz-fake-rule.tsx',
    );
    expect(fired(messages, 'no-restricted-syntax')).toHaveLength(1);
  });

  it('stays quiet when the text comes from the i18n catalog', async () => {
    const code = [
      "import { tr } from '@/i18n/tr';",
      'export function A() {',
      '  return <button type="button" aria-label={tr.ui.retry}>{tr.ui.retry}</button>;',
      '}',
    ].join('\n');
    expect(await lint(code, 'src/zz-fake-rule.tsx')).toEqual([]);
  });

  it('lets a test file hold constant text', async () => {
    expect(
      await lint('export function A() { return <p>Deneme</p>; }', 'test/zz-fake-rule.test.tsx'),
    ).toEqual([]);
  });
});

describe('import boundaries', () => {
  const forbidden: { name: string; code: string; file: string; message: RegExp }[] = [
    {
      name: "'react-router-dom'",
      code: "import { Link } from 'react-router-dom'; export const x = Link;",
      file: 'src/zz-fake-rule.ts',
      message: /react-router-dom kullanilmaz/,
    },
    {
      name: "'@mutalaa/reader-core' (not an allowed workspace package)",
      code: "import { x } from '@mutalaa/reader-core'; export { x };",
      file: 'src/zz-fake-rule.ts',
      message: /izin verilen @mutalaa/,
    },
    {
      name: "'node:fs' in src",
      code: "import { readFileSync } from 'node:fs'; export { readFileSync };",
      file: 'src/zz-fake-rule.ts',
      message: /Node modulleri/,
    },
    {
      name: "'react-native' (platform package)",
      code: "import { View } from 'react-native'; export const x = View;",
      file: 'src/zz-fake-rule.ts',
      message: /react-native/,
    },
  ];

  it.each(forbidden)('fires: $name', async ({ code, file, message }) => {
    const lines = fired(await lint(code, file), 'no-restricted-imports');
    expect(lines.length).toBe(1);
    expect(lines[0]).toMatch(message);
  });

  it("allows 'node:fs' in a test file", async () => {
    const code = "import { readFileSync } from 'node:fs'; export { readFileSync };";
    expect(await lint(code, 'test/zz-fake-rule.test.ts')).toEqual([]);
  });

  it("still forbids 'react-router-dom' in a test file", async () => {
    const code = "import { Link } from 'react-router-dom'; export const x = Link;";
    expect(
      fired(await lint(code, 'test/zz-fake-rule.test.ts'), 'no-restricted-imports'),
    ).toHaveLength(1);
  });

  it.each(['@mutalaa/anchors', '@mutalaa/search'])('allows %s', async (name) => {
    const code = `import { x } from '${name}'; export { x };`;
    expect(await lint(code, 'src/zz-fake-rule.ts')).toEqual([]);
  });
});
