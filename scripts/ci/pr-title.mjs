// PR title check (A08). The title arrives through the TITLE environment variable and is never
// interpolated into a shell command. Types and scopes mirror docs/02-mimari/03-proje-yapisi.md §6;
// .claude/hooks/test/kit.test.mjs keeps the two lists in sync.

import { pathToFileURL } from 'node:url';

export const TYPES = [
  'feat',
  'fix',
  'docs',
  'refactor',
  'perf',
  'test',
  'build',
  'ci',
  'chore',
  'data',
];
export const SCOPES = [
  'mobile',
  'editor',
  'web',
  'api',
  'server',
  'publisher',
  'pipeline',
  'anchors',
  'content-schema',
  'search',
  'reader-core',
  'player',
  'ui-tokens',
  'test-vectors',
  'infra',
  'docs',
  'kit',
];

export const MAX_SUMMARY = 72;
const PATTERN = new RegExp(`^(${TYPES.join('|')})[(](${SCOPES.join('|')})[)]: (.+)$`, 's');

/**
 * @param {string} title
 * @param {string} [author] PR author login; Dependabot summaries may exceed the length limit.
 * @returns {string[]} problems; empty when the title is valid
 */
export function checkTitle(title, author = '') {
  const problems = [];
  const m = PATTERN.exec(title);
  if (!m) {
    problems.push(
      'title must look like "<type>(<scope>): <summary>" with a type and scope from the project list',
    );
    return problems;
  }
  const summary = m[3];
  if (summary.includes('\n')) problems.push('title must be a single line');
  if (!/^[a-z0-9]/.test(summary))
    problems.push('summary must start with a lowercase letter or a digit');
  if (summary.endsWith('.')) problems.push('summary must not end with a period');
  if (author !== 'dependabot[bot]' && [...summary].length > MAX_SUMMARY) {
    problems.push(`summary must be at most ${MAX_SUMMARY} characters`);
  }
  return problems;
}

function main() {
  const title = process.env.TITLE ?? '';
  const author = process.env.AUTHOR ?? '';
  const problems = checkTitle(title, author);
  if (problems.length === 0) {
    process.stdout.write('PR title OK\n');
    return 0;
  }
  process.stdout.write('PR title is not valid:\n');
  for (const p of problems) process.stdout.write(`- ${p}\n`);
  process.stdout.write(`types:  ${TYPES.join(', ')}\n`);
  process.stdout.write(`scopes: ${SCOPES.join(', ')}\n`);
  process.stdout.write('Title received: ');
  process.stdout.write(JSON.stringify(title));
  process.stdout.write('\n');
  return 1;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exitCode = main();
}
