import { tryParse } from '@mutalaa/anchors';
import { TriangleAlertIcon } from 'lucide-react';
import { useId } from 'react';
import { Link } from 'react-router';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { trOcr } from '@/i18n/tr-ocr';
import { formatNumber } from '@/lib/format';
import type { BasmalaMeal, PipelineExtras } from '@/lib/payload';

/** Longest unknown code that is shown (a code is a short identifier; anything longer is cut). */
const MAX_SHOWN_CODE = 64;

/**
 * One warning code: its Turkish sentence, or, for a code this panel does not know, the generic message followed by
 * the raw code in a `code` element (looked up with `hasOwn`, so names such as `constructor` stay unknown).
 */
function WarningCode({ code }: { code: string }) {
  const table: Readonly<Record<string, string>> = trOcr.hat.warnings;
  if (Object.hasOwn(table, code)) return <>{table[code]}</>;
  const shown = code.length > MAX_SHOWN_CODE ? `${code.slice(0, MAX_SHOWN_CODE)}…` : code;
  return (
    <>
      {trOcr.hat.unknownWarning} <code className="break-all">{shown}</code>
    </>
  );
}

/**
 * What the content pipeline noted on a proposal (`onerilen.uyari`, `onerilen.tanik`): its warnings and the witness
 * agreement. The agreement is a text similarity to a second copy, never fidelity to the original edition, and it
 * is not called "Güven" (K-49). Nothing is drawn when the record carries neither.
 */
export function PipelineNotes({ extras }: { extras: PipelineExtras }) {
  const witnessId = useId();
  const { uyarilar, tanik } = extras;
  if (uyarilar.length === 0 && tanik === null) return null;
  return (
    <div className="flex flex-col gap-3">
      {uyarilar.length > 0 ? (
        <Alert role="note" data-testid="ocr-hat-warning">
          <TriangleAlertIcon aria-hidden="true" />
          <AlertTitle>{trOcr.hat.warningHeading}</AlertTitle>
          <AlertDescription>
            <p>{trOcr.hat.warningHint}</p>
            <ul className="list-disc pl-5">
              {uyarilar.map((code, index) => (
                <li key={index} lang="tr">
                  <WarningCode code={code} />
                </li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      ) : null}
      {tanik !== null ? (
        <section
          aria-labelledby={witnessId}
          className="flex flex-col gap-1 rounded-lg border p-3"
          data-testid="ocr-witness"
        >
          <h3 id={witnessId} className="text-sm font-medium">
            {trOcr.hat.witnessHeading}
          </h3>
          {tanik.skor !== null ? (
            <p className="text-sm">{trOcr.hat.witnessScore(formatNumber(tanik.skor))}</p>
          ) : null}
          {tanik.kapsam !== null ? (
            <p className="text-sm">
              {trOcr.hat.witnessRange(formatNumber(tanik.kapsam[0]), formatNumber(tanik.kapsam[1]))}
            </p>
          ) : null}
          {tanik.kaynak !== null ? (
            <p className="text-xs text-muted-foreground">
              {trOcr.hat.witnessSourceLabel} <code className="break-all">{tanik.kaynak}</code>
            </p>
          ) : null}
          {tanik.yontem !== null ? (
            <p className="text-xs text-muted-foreground">
              {trOcr.hat.witnessMethodLabel} <code className="break-all">{tanik.yontem}</code>
            </p>
          ) : null}
          <p className="text-xs text-muted-foreground">{trOcr.hat.witnessHint}</p>
        </section>
      ) : null}
    </div>
  );
}

/** The separately taken basmala meal (`attrs.besmele_meali`), shown apart from the unit's own text. */
export function BasmalaSection({ besmele }: { besmele: BasmalaMeal }) {
  const headingId = useId();
  return (
    <section
      aria-labelledby={headingId}
      className="flex flex-col gap-1 rounded-lg border p-3"
      data-testid="ocr-besmele"
    >
      <h3 id={headingId} className="text-sm font-medium">
        {trOcr.besmele.heading}
      </h3>
      <p lang="tr" className="text-sm whitespace-pre-wrap">
        {besmele.metin}
      </p>
      <p className="text-xs text-muted-foreground">{trOcr.besmele.hint}</p>
    </section>
  );
}

/**
 * The follower unit of a joined meal (`attrs.birlesik_ile`): it has no text of its own (K-49 madde 8), so the
 * panel says so and links to the head unit, where the text lives. Only the status approval or a rejection can be
 * given here.
 */
export function FollowerSection({ headAnchor }: { headAnchor: string | null }) {
  const headingId = useId();
  const head = headAnchor !== null && tryParse(headAnchor) !== null ? headAnchor : null;
  return (
    <section
      aria-labelledby={headingId}
      className="flex flex-col gap-2 rounded-lg border p-3"
      data-testid="ocr-follower"
    >
      <h3 id={headingId} className="text-sm font-medium">
        {trOcr.merged.followerHeading}
      </h3>
      <p className="text-sm">{trOcr.merged.followerBody}</p>
      <p className="text-sm">
        <span className="text-muted-foreground">{trOcr.merged.headLead}</span>{' '}
        {head !== null ? (
          <Link
            to={{ pathname: '/birimler', search: `?birim=${encodeURIComponent(head)}` }}
            className="inline-block min-h-6 break-all underline"
            data-testid="ocr-follower-head"
          >
            {head}
          </Link>
        ) : (
          <span>{trOcr.merged.headMissing}</span>
        )}
      </p>
    </section>
  );
}

/** "Düzelt" of a follower unit: closed on purpose (not an open question), with its reason tied by `aria-describedby`. */
export function ClosedFix() {
  const hintId = useId();
  return (
    <div className="flex flex-col gap-1">
      <div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          aria-disabled="true"
          aria-describedby={hintId}
          data-testid="ocr-follower-fix"
          className="cursor-not-allowed opacity-60 hover:bg-background hover:text-foreground dark:hover:bg-input/30"
          onClick={(event) => event.preventDefault()}
        >
          {`${trOcr.actions.fix} · ${trOcr.merged.fixClosed}`}
        </Button>
      </div>
      <p id={hintId} className="text-xs text-muted-foreground">
        {trOcr.merged.fixClosedHint}
      </p>
    </div>
  );
}
