// Runs once before the tests. Prints the effective locale and the Unicode version so that a
// run under LANG=tr_TR.UTF-8 can be told apart from a default run (windows-sorun).
export default function setup(): void {
  const locale = Intl.DateTimeFormat().resolvedOptions().locale;
  console.log(`[search] locale=${locale} unicode=${process.versions.unicode}`);
}
