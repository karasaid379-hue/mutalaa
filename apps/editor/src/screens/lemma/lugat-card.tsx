import { useId, useState, type ReactNode } from 'react';
import { labelOf, originLabel, targetLabel } from '@/i18n/labels';
import { tr } from '@/i18n/tr';
import { trLemma } from '@/i18n/tr-lemma';
import { trLugat } from '@/i18n/tr-lugat';
import { formatNumber } from '@/lib/format';
import { ReviewBadges } from '@/review/badges';
import { DecisionForm } from '@/review/decision-form';
import type { QueueDetailProps } from '@/review/queue-layout';
import type { ReviewDetail } from '@/review/types';
import { JsonBlock } from '@/screens/catalog/json-block';
import { readLugatReference } from './lugat-payload';

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-wrap gap-x-2">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="min-w-0 break-words">{children}</dd>
    </div>
  );
}

/** The madde as the API sees it now (`hedef`): the headword as stored (third party text, shown as is), nothing recomputed. */
function Snapshot({ review }: { review: ReviewDetail }) {
  const headingId = useId();
  const target = review.hedef;
  return (
    <section
      aria-labelledby={headingId}
      className="flex flex-col gap-1 rounded-lg border p-3"
      data-testid="lugat-snapshot"
    >
      <h3 id={headingId} className="text-sm font-medium">
        {trLugat.snapshot.heading}
      </h3>
      {target ? (
        <dl className="text-sm">
          <Row label={trLemma.snapshot.table}>{targetLabel(target.tablo)}</Row>
          {target.basliksoz ? (
            <Row label={trLugat.snapshot.headword}>
              <span className="font-medium" data-testid="lugat-headword">
                {target.basliksoz}
              </span>
            </Row>
          ) : null}
          {target.source ? (
            <Row label={trLugat.snapshot.source}>
              <span data-testid="lugat-source">{labelOf(trLugat.sources, target.source)}</span>
            </Row>
          ) : null}
          {target.anlam_no !== null && target.anlam_no !== undefined ? (
            <Row label={trLugat.snapshot.meaning}>
              <span data-testid="lugat-meaning">{trLugat.meaning(target.anlam_no)}</span>
            </Row>
          ) : null}
          {target.osmanlica_yazim ? (
            <Row label={trLugat.snapshot.ottoman}>{target.osmanlica_yazim}</Row>
          ) : null}
          {target.koken_dil ? (
            <Row label={trLugat.snapshot.etymology}>{target.koken_dil}</Row>
          ) : null}
          {target.duzey !== null && target.duzey !== undefined ? (
            <Row label={trLugat.snapshot.level}>{String(target.duzey)}</Row>
          ) : null}
          <Row
            label={
              target.origin === 'kaynak'
                ? trLugat.snapshot.sourceDefinition
                : trLugat.snapshot.definition
            }
          >
            {target.tanim_tr ? (
              <span lang="tr">{target.tanim_tr}</span>
            ) : (
              <span className="text-muted-foreground">{trLugat.snapshot.noDefinition}</span>
            )}
          </Row>
          {target.origin ? (
            <Row label={trLugat.snapshot.origin}>
              {labelOf(trLugat.snapshot.originNames, target.origin)}
            </Row>
          ) : null}
          {target.version ? <Row label={trLugat.snapshot.version}>{target.version}</Row> : null}
          {target.status ? (
            <Row label={trLugat.snapshot.status}>
              {labelOf(tr.labels.candidateStatus, target.status)}
            </Row>
          ) : null}
        </dl>
      ) : (
        <p className="text-sm text-muted-foreground">{trLugat.snapshot.missing}</p>
      )}
    </section>
  );
}

/**
 * The reference data of the candidate (`onerilen`: frequency, books, dictionary meanings), labelled "Başvuru
 * (onaysız)". It is shown and never applied: it is not offered as the definition (K-51 madde 10).
 */
function Reference({ review }: { review: ReviewDetail }) {
  const headingId = useId();
  const reference = readLugatReference(review.onerilen);
  return (
    <section
      aria-labelledby={headingId}
      className="flex flex-col gap-1 rounded-lg border p-3"
      data-testid="lugat-reference"
    >
      <h3 id={headingId} className="text-sm font-medium">
        {trLugat.reference.heading}
      </h3>
      <p className="text-xs text-muted-foreground">{trLugat.reference.note}</p>
      {reference ? (
        <>
          <dl className="text-sm">
            {reference.siklik !== null ? (
              <Row label={trLugat.reference.frequency}>{formatNumber(reference.siklik)}</Row>
            ) : null}
            {reference.kitaplar !== null ? (
              <Row label={trLugat.reference.books}>
                {trLugat.reference.booksCount(reference.kitaplar)}
              </Row>
            ) : null}
          </dl>
          {reference.meanings.length > 0 ? (
            <div className="flex flex-col gap-1">
              <h4 className="text-sm font-medium">{trLugat.reference.meanings}</h4>
              <ul className="text-sm" data-testid="lugat-reference-meanings">
                {reference.meanings.map((entry, index) => (
                  <li key={`${index}:${entry.anlam}`} className="flex flex-wrap gap-x-2">
                    <span lang="tr">{entry.anlam}</span>
                    {entry.sayi !== null ? (
                      <span className="text-muted-foreground">
                        {trLugat.reference.meaningEntry(entry.sayi)}
                      </span>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">{trLugat.reference.none}</p>
          )}
          {reference.known ? null : (
            <>
              <p className="text-sm text-muted-foreground">{trLugat.reference.unreadable}</p>
              <JsonBlock title={trLugat.reference.raw} value={review.onerilen} />
            </>
          )}
        </>
      ) : (
        <p className="text-sm text-muted-foreground">{trLugat.reference.none}</p>
      )}
    </section>
  );
}

function Origin({ review }: { review: ReviewDetail }) {
  const headingId = useId();
  return (
    <section
      aria-labelledby={headingId}
      className="flex flex-col gap-1 rounded-lg border p-3"
      data-testid="lugat-origin"
    >
      <h3 id={headingId} className="text-sm font-medium">
        {trLugat.origin.heading}
      </h3>
      <dl className="text-sm">
        <Row label={trLugat.origin.origin}>{originLabel(review.koken)}</Row>
        <Row label={trLugat.origin.proposer}>{review.oneren}</Row>
      </dl>
      {review.yz_modeli ? null : (
        <p className="text-xs text-muted-foreground">{trLugat.origin.noAi}</p>
      )}
    </section>
  );
}

/**
 * The card of one lügat madde review (`lugat_madde` + `tanim_tr`; K-51 madde 9, 10 and 14): the madde as stored (source name,
 * meaning number, definition and origin badge), the reference data (labelled "Başvuru (onaysız)", never approved as the
 * definition), the origin and the decision form: a definition that came from the source is approved unchanged ("Onayla")
 * or edited ("Düzenle ve onayla"); a madde without one needs the definition the editor writes.
 * There is no AI draft here (`yz_modeli` is empty): the K-25 badge is drawn by the form's shared `dogrulanmamis` rule only.
 */
export function LugatCard({ review, onDecided }: QueueDetailProps) {
  // After a 412 the form hands over the fresh record; it is shown until the parent gives a new object.
  const [refreshed, setRefreshed] = useState<{ from: ReviewDetail; to: ReviewDetail } | null>(null);
  const shown = refreshed && refreshed.from === review ? refreshed.to : review;
  return (
    <div className="flex flex-col gap-4" data-testid="lugat-card">
      <div className="flex flex-col gap-1">
        <h2 className="text-base font-semibold">{trLugat.heading}</h2>
        <ReviewBadges review={shown} showOrigin />
      </div>
      <Snapshot review={shown} />
      <Reference review={shown} />
      <Origin review={shown} />
      <p className="text-sm text-muted-foreground">{trLugat.decisionNote}</p>
      <DecisionForm
        review={review}
        onDecided={onDecided}
        onRefreshed={(fresh) => setRefreshed({ from: review, to: fresh })}
      />
    </div>
  );
}
