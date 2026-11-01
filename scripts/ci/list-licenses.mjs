// Dependency license list (A08, Teknoloji yığını §3, K-42 madde 6). Lists only; never gates a build.
//
//   node scripts/ci/list-licenses.mjs pnpm  [file]   pnpm licenses list -r --json --prod
//   node scripts/ci/list-licenses.mjs nuget [file]   nuget-license ... -o JsonPretty
//   add  --json <outfile>  to write the normalized package list (input for the open source section
//   of the Ayarlar > Kaynaklar screen, A34)
//
// The input is read from the file argument or from stdin. Exit codes: 0 the list was printed (or
// there was nothing to list), 2 unreadable input, bad arguments or an empty NuGet list.

import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

/** pnpm licenses list --json: { "<license>": [{ name, versions: [...] }] } */
export function fromPnpm(text) {
  const trimmed = String(text ?? '').trim();
  if (trimmed === '' || /^no licenses/i.test(trimmed)) return [];
  const data = JSON.parse(trimmed);
  const out = [];
  for (const [license, entries] of Object.entries(data)) {
    for (const entry of entries) {
      if (entry.name.startsWith('@mutalaa/')) continue; // workspace packages are ours
      for (const version of entry.versions?.length ? entry.versions : ['']) {
        out.push({ name: entry.name, version, license });
      }
    }
  }
  return out;
}

/** nuget-license JSON: [{ PackageId, PackageVersion, License, ValidationErrors: [{ Error }] }] */
export function fromNuget(text) {
  const data = JSON.parse(String(text ?? '[]'));
  if (!Array.isArray(data)) throw new Error('nuget-license output must be a JSON array');
  return data.map((p) => ({
    name: p.PackageId,
    version: p.PackageVersion,
    license: p.License ?? null,
    errors: (p.ValidationErrors ?? []).map((e) => e.Error ?? String(e)),
  }));
}

// Ordinal comparison: the order does not depend on the machine's locale.
const ordinal = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

const licenseOf = (p) => {
  const text = String(p.license ?? '').trim();
  return text === '' ? '(none declared)' : text;
};

/**
 * One line per package, sorted by name and version. Tool notes (nuget-license validation errors)
 * are shown next to the package; they do not change the exit code.
 * @param {{name: string, version: string, license: string | null | undefined, errors?: string[]}[]} packages
 * @returns {string[]}
 */
export function format(packages) {
  return [...packages]
    .sort((a, b) => ordinal(a.name, b.name) || ordinal(a.version, b.version))
    .map((p) => {
      const notes = p.errors?.length ? ` [${p.errors.join('; ')}]` : '';
      return `  ${p.name}@${p.version}: ${licenseOf(p)}${notes}`;
    });
}

/** Package count per license, sorted by license: "Apache-2.0 1, MIT 43". */
export function summarize(packages) {
  const counts = new Map();
  for (const p of packages) counts.set(licenseOf(p), (counts.get(licenseOf(p)) ?? 0) + 1);
  return [...counts]
    .sort(([a], [b]) => ordinal(a, b))
    .map(([license, n]) => `${license} ${n}`)
    .join(', ');
}

function main(argv) {
  const args = argv.slice(2);
  const kind = args.shift();
  let jsonOut = null;
  const positional = [];
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--json') jsonOut = args[++i] ?? '';
    else positional.push(args[i]);
  }
  if ((kind !== 'pnpm' && kind !== 'nuget') || jsonOut === '' || positional.length > 1) {
    process.stderr.write('usage: list-licenses.mjs <pnpm|nuget> [file] [--json outfile]\n');
    return 2;
  }
  let text;
  try {
    text = positional[0] ? fs.readFileSync(positional[0], 'utf8') : fs.readFileSync(0, 'utf8');
  } catch (err) {
    process.stderr.write(`cannot read input: ${err.message}\n`);
    return 2;
  }
  let packages;
  try {
    packages = kind === 'pnpm' ? fromPnpm(text) : fromNuget(text);
  } catch (err) {
    process.stderr.write(`cannot parse input: ${err.message}\n`);
    return 2;
  }
  if (jsonOut) fs.writeFileSync(jsonOut, `${JSON.stringify(packages, null, 2)}\n`, 'utf8');
  if (packages.length === 0) {
    if (kind === 'nuget') {
      // The server always has NuGet dependencies; an empty list means the tool or the project
      // filter produced nothing, and the list would silently miss every package.
      process.stderr.write(
        'nuget: no packages found; the tool output is empty or every project was excluded\n',
      );
      return 2;
    }
    process.stdout.write(`${kind}: no shipped dependencies to list\n`);
    return 0;
  }
  process.stdout.write(`${kind}: ${packages.length} packages\n`);
  for (const line of format(packages)) process.stdout.write(`${line}\n`);
  process.stdout.write(`licenses: ${summarize(packages)}\n`);
  return 0;
}

// Node loads the main module by its real path while argv[1] is only resolved, so compare real paths.
if (
  process.argv[1] &&
  fs.realpathSync(process.argv[1]) === fs.realpathSync(fileURLToPath(import.meta.url))
) {
  process.exitCode = main(process.argv);
}
