// Runs once before the tests. Prints the effective locale and the Unicode version so that a
// run under LANG=tr_TR.UTF-8 can be told apart from a default run (windows-sorun).
// On non-Windows hosts it also fails when a Turkish locale was requested but ICU resolved another
// one, so a tr_TR CI leg cannot silently run as English (A08).
export default function setup(): void {
  const locale = Intl.DateTimeFormat().resolvedOptions().locale;
  console.log(`[search] locale=${locale} unicode=${process.versions.unicode}`);
  const requested = process.env.LC_ALL || process.env.LC_MESSAGES || process.env.LANG || '';
  if (process.platform !== 'win32' && requested.startsWith('tr_TR') && !locale.startsWith('tr')) {
    throw new Error(`Requested locale ${requested} but ICU resolved ${locale}.`);
  }
}
