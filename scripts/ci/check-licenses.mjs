// Dependency license gate (A08, Teknoloji yığını §3). Not legal advice (hukuki görüş değildir).
//
//   node scripts/ci/check-licenses.mjs pnpm  [file]   pnpm licenses list -r --json --prod
//   node scripts/ci/check-licenses.mjs nuget [file]   nuget-license ... -o JsonPretty
//   add  --json <outfile>  to write the normalized package list (input for THIRD_PARTY_NOTICES, A34)
//
// The input is read from the file argument or from stdin. Exit codes: 0 all licenses allowed (or
// nothing to check), 1 at least one disallowed or unknown license, 2 unreadable input.
//
// Policy: only code that ships (mobile, editor, web) or is served over the network (API) is checked.
// The content pipeline is never distributed, so it is only listed (ci-pipeline), not gated.
// LGPL is allowed (dynamic linking); GPL, AGPL, SSPL, BUSL, commercial, UNLICENSED and unknown
// licenses are not. Content licenses are separate (K-06).

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const ALLOWED = new Set(
  [
    'MIT',
    'MIT-0',
    'Apache-2.0',
    'BSD-2-Clause',
    'BSD-3-Clause',
    'ISC',
    '0BSD',
    'Unlicense',
    'CC0-1.0',
    'PostgreSQL',
    'Zlib',
    'BlueOak-1.0.0',
    'Python-2.0',
    'MPL-2.0',
    'LGPL-2.1',
    'LGPL-2.1-only',
    'LGPL-2.1-or-later',
    'LGPL-3.0',
    'LGPL-3.0-only',
    'LGPL-3.0-or-later',
  ].map((s) => s.toLowerCase()),
);

const COPYLEFT = /^(a?gpl|sspl|busl|eupl|osl|cpal|rpl)([-0-9.]|$)/i;

/** @param {string} expr SPDX expression; returns tokens or throws */
function tokenize(expr) {
  const tokens = [];
  const re = /\s*([()]|[^\s()]+)/gy;
  let m;
  while ((m = re.exec(expr)) !== null) tokens.push(m[1]);
  return tokens;
}

/**
 * Evaluates an SPDX license expression. OR passes when any alternative is allowed, AND requires
 * every term, WITH exceptions are ignored. A trailing "+" ("LGPL-3.0+") is treated as "-or-later".
 * @returns {{ ok: boolean, reason: string }}
 */
export function evaluate(expression) {
  const text = String(expression ?? '').trim();
  if (text === '') return { ok: false, reason: 'no license' };
  const tokens = tokenize(text);
  let pos = 0;
  const reasons = [];

  const id = (raw) => {
    let name = raw;
    if (name.endsWith('+')) name = `${name.slice(0, -1)}-or-later`;
    if (ALLOWED.has(name.toLowerCase())) return true;
    reasons.push(COPYLEFT.test(raw) ? `${raw} (copyleft)` : `${raw} (not on the allowed list)`);
    return false;
  };

  // grammar: or := and ('OR' and)* ; and := term ('AND' term)* ; term := '(' or ')' | id ('WITH' id)?
  const parseTerm = () => {
    const t = tokens[pos++];
    if (t === undefined) throw new Error('unexpected end');
    if (t === '(') {
      const v = parseOr();
      if (tokens[pos++] !== ')') throw new Error('missing )');
      return v;
    }
    if (t === ')' || /^(and|or|with)$/i.test(t)) throw new Error(`unexpected ${t}`);
    const ok = id(t);
    if (tokens[pos] && /^with$/i.test(tokens[pos])) pos += 2;
    return ok;
  };
  const parseAnd = () => {
    let v = parseTerm();
    while (tokens[pos] && /^and$/i.test(tokens[pos])) {
      pos++;
      const r = parseTerm();
      v = v && r;
    }
    return v;
  };
  const parseOr = () => {
    let v = parseAnd();
    while (tokens[pos] && /^or$/i.test(tokens[pos])) {
      pos++;
      const r = parseAnd();
      v = v || r;
    }
    return v;
  };

  try {
    const ok = parseOr();
    if (pos !== tokens.length) throw new Error(`unexpected ${tokens[pos]}`);
    return ok ? { ok: true, reason: '' } : { ok: false, reason: reasons.join('; ') };
  } catch (err) {
    return { ok: false, reason: `unparseable license expression "${text}" (${err.message})` };
  }
}

// An exception covers exactly one version: "name@version". A new version must be reviewed again.
function matches(exception, name, version) {
  return exception.package === `${name}@${version}`;
}

/**
 * Exceptions file format: [{ "package": "name@version", "license": "...", "source": "https://...",
 * "date": "YYYY-MM-DD", "note": "..." }]. "package" must carry a version and "source" is required.
 * @returns {string[]} problems
 */
export function validateExceptions(data) {
  if (!Array.isArray(data)) return ['the exceptions file must contain a JSON array'];
  const problems = [];
  data.forEach((e, i) => {
    if (typeof e?.package !== 'string' || !/^.+@[^@]+$/.test(e.package)) {
      problems.push(`entry ${i}: "package" must look like "name@version"`);
    }
    if (typeof e?.source !== 'string' || e.source.trim() === '') {
      problems.push(`entry ${i}: "source" is required`);
    }
  });
  return problems;
}

/**
 * @param {{name: string, version: string, license: string | null | undefined, errors?: string[]}[]} packages
 * @param {{package: string}[]} exceptions
 */
export function check(packages, exceptions = []) {
  const violations = [];
  const excepted = [];
  for (const p of packages) {
    const result =
      p.errors && p.errors.length
        ? { ok: false, reason: p.errors.join('; ') }
        : evaluate(p.license);
    if (result.ok) continue;
    const ex = exceptions.find((e) => matches(e, p.name, p.version));
    if (ex) excepted.push({ ...p, reason: result.reason, exception: ex });
    else violations.push({ ...p, reason: result.reason });
  }
  return { checked: packages.length, violations, excepted };
}

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
  return data.map((p) => ({
    name: p.PackageId,
    version: p.PackageVersion,
    license: p.License ?? null,
    errors: (p.ValidationErrors ?? []).map((e) => e.Error ?? String(e)),
  }));
}

function readExceptions(file) {
  if (!fs.existsSync(file)) return [];
  const data = JSON.parse(fs.readFileSync(file, 'utf8'));
  const problems = validateExceptions(data);
  if (problems.length) throw new Error(`license-exceptions.json: ${problems.join('; ')}`);
  return data;
}

function main(argv) {
  const args = argv.slice(2);
  const kind = args.shift();
  let jsonOut = null;
  const positional = [];
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--json') jsonOut = args[++i];
    else positional.push(args[i]);
  }
  if (kind !== 'pnpm' && kind !== 'nuget') {
    process.stderr.write('usage: check-licenses.mjs <pnpm|nuget> [file] [--json outfile]\n');
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
  let exceptions;
  try {
    packages = kind === 'pnpm' ? fromPnpm(text) : fromNuget(text);
    exceptions = readExceptions(
      path.join(path.dirname(fileURLToPath(import.meta.url)), 'license-exceptions.json'),
    );
  } catch (err) {
    process.stderr.write(`cannot parse input: ${err.message}\n`);
    return 2;
  }
  if (jsonOut) fs.writeFileSync(jsonOut, `${JSON.stringify(packages, null, 2)}\n`, 'utf8');
  if (packages.length === 0) {
    if (kind === 'nuget') {
      // The server always has NuGet dependencies; an empty list means the tool or the project
      // filter produced nothing, and a green gate over nothing would be a false pass.
      process.stderr.write(
        'nuget: no packages found; the tool output is empty or every project was excluded\n',
      );
      return 2;
    }
    process.stdout.write(`${kind}: no shipped dependencies to check\n`);
    return 0;
  }
  const result = check(packages, exceptions);
  process.stdout.write(`${kind}: ${result.checked} packages checked\n`);
  for (const e of result.excepted) {
    process.stdout.write(
      `  exception: ${e.name}@${e.version} (${e.license}) - ${e.exception.source ?? 'no source'}\n`,
    );
  }
  for (const v of result.violations) {
    process.stdout.write(`  DISALLOWED: ${v.name}@${v.version}: ${v.reason}\n`);
  }
  return result.violations.length ? 1 : 0;
}

// Node loads the main module by its real path while argv[1] is only resolved, so compare real paths.
if (
  process.argv[1] &&
  fs.realpathSync(process.argv[1]) === fs.realpathSync(fileURLToPath(import.meta.url))
) {
  process.exitCode = main(process.argv);
}
