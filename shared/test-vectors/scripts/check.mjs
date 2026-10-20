// CLI: node scripts/check.mjs [folder-or-file ...]
// No argument: scans the vector folders of this package. Exit codes: 0 clean (or no vectors),
// 1 format violations, 2 usage error (path not found).
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { DEFAULT_SKIP, checkPaths } from './check-lib.mjs';

const args = process.argv.slice(2);
const packageRoot = fileURLToPath(new URL('..', import.meta.url));

const roots = args.length > 0 ? args : [packageRoot];
const skip = args.length > 0 ? new Set() : DEFAULT_SKIP;

for (const root of roots) {
  if (!existsSync(root)) {
    console.error(`test-vectors check: path not found: ${root}`);
    process.exit(2);
  }
}

const { files, problems } = checkPaths(roots, skip);

if (files === 0) {
  console.log('test-vectors check: no vector files found, nothing to check.');
  process.exit(0);
}

for (const { file, line, message } of problems) {
  console.error(`${file}${line > 0 ? `:${line}` : ''}: ${message}`);
}

if (problems.length > 0) {
  console.error(`test-vectors check: ${problems.length} problem(s) in ${files} file(s).`);
  process.exit(1);
}

console.log(`test-vectors check: ${files} file(s) OK.`);
