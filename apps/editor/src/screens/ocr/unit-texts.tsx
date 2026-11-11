import { useId } from 'react';
import { useApi } from '@/app/api-context';
import { ArabicText } from '@/components/arabic-text';
import { ProblemMessage } from '@/components/problem-message';
import { trOcr } from '@/i18n/tr-ocr';
import { ayahAnchors } from './ayah-anchors';

/** One Tanzil ayah as the API gives it (`GET /units/{anchor}`); the text is drawn as stored (K-26). */
function AyahText({ anchor }: { anchor: string }) {
  const api = useApi();
  const unit = api.$api.useQuery(
    'get',
    '/api/v1/units/{anchor}',
    { params: { path: { anchor } } },
    { retry: false },
  );
  return (
    <li className="flex flex-col gap-1" aria-busy={unit.isPending ? 'true' : undefined}>
      <span className="text-xs text-muted-foreground break-all">{anchor}</span>
      {unit.isPending ? (
        <span className="text-sm text-muted-foreground">{trOcr.ayah.loading}</span>
      ) : unit.isError ? (
        <div className="flex flex-col gap-1">
          <span className="text-sm font-medium">{trOcr.ayah.failed}</span>
          <ProblemMessage error={unit.error} />
        </div>
      ) : (
        <ArabicText as="p" text={unit.data.metin} />
      )}
    </li>
  );
}

/**
 * The Tanzil ayah(s) the reviewed unit belongs to. A meal anchor gives its ayah; the head unit of a joined meal
 * carries `attrs.kapsam` (`q:{sure}:{ilk}-{son}`), and then the ayahs of that range are shown (K-49 madde 8).
 */
export function AyahSection({ anchor, kapsam }: { anchor: string; kapsam?: string | null }) {
  const headingId = useId();
  const range = kapsam ? ayahAnchors(kapsam) : null;
  // A range that cannot be read is ignored: the ayah of the unit's own anchor is shown instead.
  const scope: string | null = kapsam && range !== null && range.shown.length > 0 ? kapsam : null;
  const ayahs = scope !== null && range !== null ? range : ayahAnchors(anchor);
  return (
    <section
      aria-labelledby={headingId}
      className="flex flex-col gap-2 rounded-lg border p-3"
      data-testid="ocr-ayah"
    >
      <h3 id={headingId} className="text-sm font-medium">
        {trOcr.ayah.heading}
      </h3>
      {scope !== null ? (
        <p className="text-xs text-muted-foreground" data-testid="ocr-ayah-scope">
          {trOcr.merged.scope(scope)}
        </p>
      ) : null}
      {ayahs.shown.length === 0 ? (
        <p className="text-sm text-muted-foreground">{trOcr.ayah.none}</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {ayahs.shown.map((shown) => (
            <AyahText key={shown} anchor={shown} />
          ))}
        </ul>
      )}
      {ayahs.hidden > 0 ? (
        <p className="text-xs text-muted-foreground">{trOcr.ayah.more(ayahs.hidden)}</p>
      ) : null}
    </section>
  );
}

/** The current text of the reviewed unit (its meal), as stored. */
export function UnitTextSection({ heading, text }: { heading: string; text: string }) {
  const headingId = useId();
  return (
    <section
      aria-labelledby={headingId}
      className="flex flex-col gap-1 rounded-lg border p-3"
      data-testid="ocr-unit-text"
    >
      <h3 id={headingId} className="text-sm font-medium">
        {heading}
      </h3>
      {text === '' ? (
        <p className="text-sm text-muted-foreground">{trOcr.text.empty}</p>
      ) : (
        <p lang="tr" className="text-sm whitespace-pre-wrap">
          {text}
        </p>
      )}
    </section>
  );
}
