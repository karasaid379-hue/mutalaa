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
    <li className="flex flex-col gap-1">
      <span className="text-xs text-muted-foreground break-all">{anchor}</span>
      {unit.isPending ? (
        <span className="text-sm text-muted-foreground">{trOcr.ayah.loading}</span>
      ) : unit.isError ? (
        <span className="flex flex-col gap-1">
          <span className="text-sm font-medium">{trOcr.ayah.failed}</span>
          <ProblemMessage error={unit.error} />
        </span>
      ) : (
        <ArabicText as="p" text={unit.data.metin} />
      )}
    </li>
  );
}

/** The Tanzil ayah(s) the reviewed unit belongs to (a meal anchor gives its ayah; a joined meal gives two). */
export function AyahSection({ anchor }: { anchor: string }) {
  const headingId = useId();
  const ayahs = ayahAnchors(anchor);
  return (
    <section
      aria-labelledby={headingId}
      className="flex flex-col gap-2 rounded-lg border p-3"
      data-testid="ocr-ayah"
    >
      <h3 id={headingId} className="text-sm font-medium">
        {trOcr.ayah.heading}
      </h3>
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
