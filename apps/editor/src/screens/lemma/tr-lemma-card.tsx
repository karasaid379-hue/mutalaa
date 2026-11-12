import { useId, useState, type ReactNode } from 'react';
import type { components } from '@/api/schema';
import { ArabicText } from '@/components/arabic-text';
import { Badge } from '@/components/ui/badge';
import { labelOf } from '@/i18n/labels';
import { tr } from '@/i18n/tr';
import { trLemma } from '@/i18n/tr-lemma';
import { formatNumber } from '@/lib/format';
import { readObjectionReason, readRootMapping } from '@/lib/payload';
import { ReviewBadges } from '@/review/badges';
import { DecisionForm } from '@/review/decision-form';
import type { QueueDetailProps } from '@/review/queue-layout';
import { isObjectionReview } from '@/review/rules';
import type { ReviewDetail } from '@/review/types';
import { JsonBlock } from '@/screens/catalog/json-block';
import { ApprovalBadge } from './approval-badge';
import { approvalLabel, readApprovalPath } from './approval';
import { EtymologyForm, ObjectionForm } from './lemma-action-forms';
import { readLemmaId } from './payload';

type Target = NonNullable<ReviewDetail['hedef']>;
type Evidence = components['schemas']['LemmaKanitSummary'];
type KwicItem = components['schemas']['TrKwicItem'];

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-wrap gap-x-2">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="min-w-0 break-words">{children}</dd>
    </div>
  );
}

function Section({
  title,
  testId,
  children,
}: {
  title: string;
  testId: string;
  children: ReactNode;
}) {
  const headingId = useId();
  return (
    <section
      aria-labelledby={headingId}
      className="flex min-w-0 flex-col gap-1 rounded-lg border p-3"
      data-testid={testId}
    >
      <h3 id={headingId} className="text-sm font-medium">
        {title}
      </h3>
      {children}
    </section>
  );
}

function yesNo(value: boolean): string {
  return value ? trLemma.kok.yes : trLemma.kok.no;
}

/** The Turkish lemma and its mapping as the API sees it now (`hedef`): nothing is recomputed. */
function Summary({ review, target }: { review: ReviewDetail; target: Target | null | undefined }) {
  const proposal = readRootMapping(review.onerilen);
  const path = readApprovalPath(target?.onay_yolu);
  const isCandidate = target?.status === 'aday';
  return (
    <Section title={trLemma.snapshot.heading} testId="tr-lemma-summary">
      {target ? (
        <dl className="text-sm">
          {target.lemma_id !== null && target.lemma_id !== undefined ? (
            <Row label={trLemma.snapshot.lemmaId}>{String(target.lemma_id)}</Row>
          ) : null}
          {target.text ? (
            <Row label={trLemma.kok.lemma}>
              <span lang="tr" className="font-medium">
                {target.text}
              </span>
            </Row>
          ) : null}
          <Row label={isCandidate ? trLemma.kok.proposedRoot : trLemma.kok.root}>
            {target.root_letters ? (
              <ArabicText text={target.root_letters} className="text-xl" />
            ) : (
              trLemma.kok.none
            )}
          </Row>
          {target.root_id !== null && target.root_id !== undefined ? (
            <Row label={trLemma.kok.rootId}>{String(target.root_id)}</Row>
          ) : null}
          <Row label={trLemma.kok.arLemma}>
            {target.ar_lemma_text ? (
              <ArabicText text={target.ar_lemma_text} className="text-xl" />
            ) : (
              trLemma.kok.none
            )}
          </Row>
          {target.ar_lemma_id !== null && target.ar_lemma_id !== undefined ? (
            <Row label={trLemma.kok.arLemmaId}>{String(target.ar_lemma_id)}</Row>
          ) : null}
          {target.freq !== null && target.freq !== undefined ? (
            <Row label={trLemma.kok.freq}>{formatNumber(target.freq)}</Row>
          ) : null}
          {target.etymological_only !== null && target.etymological_only !== undefined ? (
            <Row label={trLemma.kok.etymologicalOnly}>{yesNo(target.etymological_only)}</Row>
          ) : null}
          {target.status ? (
            <Row label={trLemma.kok.status}>
              {labelOf(tr.labels.candidateStatus, target.status)}
            </Row>
          ) : null}
          <Row label={trLemma.kok.approvalPath}>
            {path ? approvalLabel(path) : trLemma.kok.none}
          </Row>
        </dl>
      ) : (
        <p className="text-sm text-muted-foreground">{trLemma.kok.missing}</p>
      )}
      {proposal ? (
        <div className="flex flex-col gap-1" data-testid="tr-lemma-proposal">
          <h4 className="text-xs font-medium">{trLemma.kok.proposal}</h4>
          <dl className="text-sm">
            {proposal.rootId !== null ? (
              <Row label={trLemma.kok.rootId}>{String(proposal.rootId)}</Row>
            ) : null}
            {proposal.arLemmaId !== null ? (
              <Row label={trLemma.kok.arLemmaId}>{String(proposal.arLemmaId)}</Row>
            ) : null}
            {proposal.etymologicalOnly !== null ? (
              <Row label={trLemma.kok.etymologicalOnly}>{yesNo(proposal.etymologicalOnly)}</Row>
            ) : null}
          </dl>
        </div>
      ) : review.onerilen !== null &&
        review.onerilen !== undefined &&
        !isObjectionReview(review) ? (
        <JsonBlock title={trLemma.kok.proposalRaw} value={review.onerilen} />
      ) : null}
    </Section>
  );
}

/** The evidence summary of the pipeline (`kanit_ozeti`): only the fields it has; nothing is made up. */
function EvidenceSection({ evidence }: { evidence: Evidence | null | undefined }) {
  const text = trLemma.kok.evidence;
  return (
    <Section title={text.heading} testId="tr-lemma-evidence">
      {evidence ? (
        <dl className="text-sm">
          {evidence.kaynak_sayisi !== null && evidence.kaynak_sayisi !== undefined ? (
            <Row label={text.sources}>{formatNumber(evidence.kaynak_sayisi)}</Row>
          ) : null}
          {evidence.qac_eslesme ? <Row label={text.qac}>{evidence.qac_eslesme}</Row> : null}
          {evidence.karar ? <Row label={text.decision}>{evidence.karar}</Row> : null}
          {evidence.neden ? <Row label={text.reason}>{evidence.neden}</Row> : null}
          {evidence.politika_surumu ? (
            <Row label={text.policy}>
              <span dir="ltr">{evidence.politika_surumu}</span>
            </Row>
          ) : null}
        </dl>
      ) : (
        <p className="text-sm text-muted-foreground">{text.none}</p>
      )}
    </Section>
  );
}

/**
 * One KWIC line of the meal: the word highlighted in its context. A line with a null part is a text that is no
 * longer current (the meal changed after the pipeline ran), so it is marked and no half sentence is drawn.
 */
function KwicLine({ item }: { item: KwicItem }) {
  const text = trLemma.kok.kwic;
  const stale = item.sol === null || item.kelime === null || item.sag === null;
  return (
    <li className="flex flex-col gap-1 rounded-md border p-2" data-testid="tr-kwic-item">
      <p className="text-xs text-muted-foreground">
        {`${text.anchor}: `}
        <code dir="ltr" className="break-all">
          {item.capa}
        </code>
      </p>
      {stale ? (
        <p className="text-sm font-medium" data-testid="tr-kwic-stale">
          {text.stale}
        </p>
      ) : (
        <p lang="tr" className="text-sm whitespace-pre-wrap">
          {item.sol}
          <mark className="rounded bg-primary/20 px-0.5 text-foreground">{item.kelime}</mark>
          {item.sag}
        </p>
      )}
    </li>
  );
}

function KwicSection({ rows }: { rows: KwicItem[] | null | undefined }) {
  const text = trLemma.kok.kwic;
  return (
    <Section title={text.heading} testId="tr-lemma-kwic">
      {rows && rows.length > 0 ? (
        <>
          <p className="text-xs text-muted-foreground">{text.note}</p>
          <ul className="flex flex-col gap-2">
            {rows.map((item) => (
              <KwicLine key={item.capa} item={item} />
            ))}
          </ul>
        </>
      ) : (
        <p className="text-sm text-muted-foreground" data-no-data="true">
          {text.none}
        </p>
      )}
    </Section>
  );
}

/**
 * The card of a Turkish lemma root mapping review (`lemma` + `kok_eslemesi`, A18.2; K-51 madde 9): the lemma, the
 * proposed root letters (Arabic, right to left) and Arabic lemma, frequency, the KWIC lines, the evidence
 * summary and the approval path. An automatic approval is shown as such (never as an editor approval); it can
 * be objected to, and the "yalnızca etimolojik" mark of an approved mapping can be changed. A candidate is
 * approved as it is, edited and approved, or rejected with the decision form.
 */
export function TrLemmaCard({ review, onDecided }: QueueDetailProps) {
  // After a 412 the form hands over the fresh record; it is shown until the parent gives a new object.
  const [refreshed, setRefreshed] = useState<{ from: ReviewDetail; to: ReviewDetail } | null>(null);
  const shown = refreshed && refreshed.from === review ? refreshed.to : review;
  const target = shown.hedef;
  const path = readApprovalPath(target?.onay_yolu);
  const objection = isObjectionReview(shown);
  const objectionReason = readObjectionReason(shown.onerilen);
  const lemmaId = readLemmaId(shown);
  const approved = target?.status === 'onayli';
  const canObject = approved && path === 'otomatik' && !objection && lemmaId !== null;
  const canMark =
    approved &&
    target?.lang === 'tr' &&
    lemmaId !== null &&
    target.root_id !== null &&
    target.root_id !== undefined;
  return (
    <div className="flex flex-col gap-4" data-testid="lemma-card">
      <div className="flex flex-col gap-1">
        <h2 className="text-base font-semibold">{trLemma.heading.kok}</h2>
        <span className="flex flex-wrap items-center gap-1">
          <ReviewBadges review={shown} showOrigin />
          {path ? <ApprovalBadge path={path} /> : null}
          {target?.status === 'aday' ? (
            <Badge variant="outline" data-testid="candidate-badge">
              {trLemma.approval.aday}
            </Badge>
          ) : null}
          {objection ? <Badge variant="outline">{trLemma.approval.objection}</Badge> : null}
        </span>
      </div>
      <Summary review={shown} target={target} />
      {objection ? (
        <p className="text-sm" data-testid="objection-note">
          {objectionReason !== null ? (
            <>
              <span className="text-muted-foreground">{`${trLemma.kok.objectionReason}: `}</span>
              <span lang="tr">{objectionReason}</span>
            </>
          ) : null}
        </p>
      ) : null}
      <EvidenceSection evidence={target?.kanit_ozeti} />
      <KwicSection rows={target?.kwic} />
      {canMark && lemmaId !== null ? (
        <EtymologyForm
          reviewId={shown.id}
          lemmaId={lemmaId}
          current={target?.etymological_only === true}
        />
      ) : target?.status === 'aday' ? (
        <Section title={trLemma.kok.etym.heading} testId="lemma-etymology">
          <p className="text-sm text-muted-foreground">{trLemma.kok.etym.candidateNote}</p>
        </Section>
      ) : approved ? (
        <Section title={trLemma.kok.etym.heading} testId="lemma-etymology">
          <p className="text-sm text-muted-foreground">{trLemma.kok.etym.noRoot}</p>
        </Section>
      ) : null}
      {canObject && lemmaId !== null ? (
        <ObjectionForm reviewId={shown.id} lemmaId={lemmaId} />
      ) : null}
      <p className="text-sm text-muted-foreground">
        {objection ? trLemma.decisionNote.itiraz : trLemma.decisionNote.kok}
      </p>
      <DecisionForm
        review={review}
        onDecided={onDecided}
        onRefreshed={(fresh) => setRefreshed({ from: review, to: fresh })}
      />
    </div>
  );
}
