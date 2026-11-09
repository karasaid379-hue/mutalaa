import { randomUUID } from 'node:crypto';
import { mkdirSync, readFileSync, rmSync } from 'node:fs';
import { DatabaseSync } from 'node:sqlite';
import { fileURLToPath } from 'node:url';

/** One entry of sql/paketler.json. */
export interface PaketTuru {
  desen: string;
  ddl: string[];
  sonra: string[];
}

interface PaketlerDosyasi {
  version: number;
  turler: Record<string, PaketTuru>;
}

export const SQL_DIZINI = fileURLToPath(new URL('../../sql/', import.meta.url));

/** Scratch root inside the project: <repo>/.tmp/a12-duzenek/. No system temp directory. */
const GECICI_KOK = fileURLToPath(new URL('../../../../.tmp/a12-duzenek/', import.meta.url));

export function loadSql(name: string): string {
  return readFileSync(new URL(name, new URL('../../sql/', import.meta.url)), 'utf8');
}

export function loadPaketler(): PaketlerDosyasi {
  return JSON.parse(loadSql('paketler.json')) as PaketlerDosyasi;
}

export function paketTuru(tur: string): PaketTuru {
  const girdi = loadPaketler().turler[tur];
  if (girdi === undefined) {
    throw new Error(`Bilinmeyen paket turu: ${tur}`);
  }
  return girdi;
}

const acikVeritabanlari = new Set<DatabaseSync>();
const geciciKlasorler = new Set<string>();

/** Creates a fresh scratch directory <repo>/.tmp/a12-duzenek/<random>/; removed by cleanup(). */
export function newTempDir(): string {
  const klasor = `${GECICI_KOK}${randomUUID()}/`;
  mkdirSync(klasor, { recursive: true });
  geciciKlasorler.add(klasor);
  return klasor;
}

/** Applies the type's ddl file list, in order, to a (new) database file and returns the open handle. */
export function buildPack(tur: string, dosyaYolu: string): DatabaseSync {
  const db = new DatabaseSync(dosyaYolu);
  acikVeritabanlari.add(db);
  for (const dosya of paketTuru(tur).ddl) {
    db.exec(loadSql(dosya));
  }
  return db;
}

/** Runs the type's post-write files (rebuild / rank / optimize). */
export function runAfter(db: DatabaseSync, tur: string): void {
  for (const dosya of paketTuru(tur).sonra) {
    db.exec(loadSql(dosya));
  }
}

/** Closes every database opened by buildPack and deletes the scratch directories. */
export function cleanup(): void {
  for (const db of acikVeritabanlari) {
    try {
      db.close();
    } catch {
      // already closed
    }
  }
  acikVeritabanlari.clear();
  for (const klasor of geciciKlasorler) {
    rmSync(klasor, { recursive: true, force: true });
  }
  geciciKlasorler.clear();
}
