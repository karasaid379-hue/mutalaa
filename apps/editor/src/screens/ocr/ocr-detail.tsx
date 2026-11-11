import { tryParse } from '@mutalaa/anchors';
import { useApi } from '@/app/api-context';
import { OpenQuestionButton } from '@/components/open-question-button';
import { ProblemMessage } from '@/components/problem-message';
import { Skeleton } from '@/components/ui/skeleton';
import { trOcr } from '@/i18n/tr-ocr';
import { readMealAttrs, readPipelineExtras, type MealAttrs } from '@/lib/payload';
import { ApprovalStages, ReviewBadges } from '@/review/badges';
import { DecisionForm } from '@/review/decision-form';
import type { QueueDetailProps } from '@/review/queue-layout';
import {
  IMMUTABLE_SOURCE_KIND,
  IMMUTABLE_UNIT_KIND,
  canEditValue,
  hasOffsetData,
  isFirstStageUnitText,
} from '@/review/rules';
import type { ReviewDetail, UnitDetail } from '@/review/types';
import { ayahAnchors } from './ayah-anchors';
import { BasmalaSection, ClosedFix, FollowerSection, PipelineNotes } from './meal-notes';
import { ProposalDiff } from './proposal-diff';
import { ScanViewer } from './scan-viewer';
import { readScanRef } from './scan-ref';
import { SourceLine } from './source-line';
import { AyahSection, UnitTextSection } from './unit-texts';

/** The page image area: a notice while the unit is unknown or has no image mapping, the viewer otherwise. */
function ScanArea({ unit }: { unit: UnitDetail }) {
  const ref = readScanRef(unit.attrs);
  if (ref === null) {
    // No request is made: scanning and the page mapping are left to S-15 (K-49), so the hand-over fields are undefined.
    return (
      <section
        aria-label={trOcr.scan.heading}
        className="flex flex-col gap-1 rounded-lg border border-dashed p-3"
        data-testid="scan-not-mapped"
      >
        <h3 className="text-sm font-medium">{trOcr.scan.heading}</h3>
        <p className="text-sm font-medium">{trOcr.scan.notMapped}</p>
        <p className="text-xs text-muted-foreground">{trOcr.scan.notMappedHint}</p>
      </section>
    );
  }
  return <ScanViewer key={`${ref.baski}/${ref.sayfa}`} baski={ref.baski} sayfa={ref.sayfa} />;
}

/**
 * What "Düzelt" means for this record: the edit field of the decision form, the closed button of a joined meal
 * follower, the A20 question for a unit with offset data, or a reason.
 */
function CorrectSection({
  review,
  unit,
  meal,
}: {
  review: ReviewDetail;
  unit: UnitDetail;
  meal: MealAttrs;
}) {
  const immutable = unit.kind === IMMUTABLE_UNIT_KIND || unit.kaynak_tur === IMMUTABLE_SOURCE_KIND;
  let body;
  if (immutable) {
    // Tanzil text: no correction control at all.
    body = <p className="text-sm text-muted-foreground">{trOcr.correct.immutable}</p>;
  } else if (meal.follower) {
    // The text of a joined meal is on its head unit (K-49 madde 8): closed, with the reason.
    body = <ClosedFix />;
  } else if (canEditValue(review, unit)) {
    body = <p className="text-sm text-muted-foreground">{trOcr.correct.openHint}</p>;
  } else if (isFirstStageUnitText(review) && unit.duzeltilebilir && hasOffsetData(unit)) {
    body = (
      <div className="flex flex-col gap-2">
        <p className="text-sm text-muted-foreground">{trOcr.correct.offsetBlocked}</p>
        <div>
          <OpenQuestionButton label={trOcr.actions.fix} phase="A20" />
        </div>
      </div>
    );
  } else {
    body = <p className="text-sm text-muted-foreground">{trOcr.correct.notAvailable}</p>;
  }
  return (
    <section
      aria-label={trOcr.correct.heading}
      className="flex flex-col gap-1"
      data-testid="ocr-correct"
    >
      <h3 className="text-sm font-medium">{trOcr.correct.heading}</h3>
      {body}
    </section>
  );
}

/**
 * Detail of an OCR or meal record (`unit` / `metin`): the source and its edition label, the page image, the Tanzil
 * ayah (the covered range of a joined meal), the current text, the pipeline's warning and witness agreement, the
 * basmala meal, the difference between the previous and the proposed text, the actions that have no API
 * counterpart yet (closed, "Açık soru: S-15") and the decision form. Correcting is approving with an edited text:
 * the form shows the edit field when `canEditValue` allows it (never for a Tanzil ayah, a unit with offset data or
 * a joined meal follower).
 */
export function OcrDetail({ review, onDecided }: QueueDetailProps) {
  const api = useApi();
  const unit = api.$api.useQuery(
    'get',
    '/api/v1/units/{anchor}',
    { params: { path: { anchor: review.hedef_anahtar } } },
    { retry: false },
  );
  const parsed = ayahAnchors(review.hedef_anahtar);
  const textHeading =
    tryParse(review.hedef_anahtar)?.anchor.t === 'meal' ? trOcr.text.meal : trOcr.text.unit;
  const meal = readMealAttrs(unit.data?.attrs);
  const extras = readPipelineExtras(review.onerilen);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h2 className="text-base font-semibold">{trOcr.detailHeading}</h2>
        <p className="text-sm break-all">{review.hedef_anahtar}</p>
        <SourceLine anchor={review.hedef_anahtar} />
        <ReviewBadges review={review} showOrigin />
      </div>

      {unit.isPending ? (
        <div className="flex flex-col gap-2" data-testid="ocr-unit-loading" aria-busy="true">
          <p className="text-sm text-muted-foreground">{trOcr.unitLoading}</p>
          <Skeleton className="h-40" />
        </div>
      ) : unit.isError ? (
        <div className="flex flex-col gap-2">
          <p className="text-sm font-medium">{trOcr.unitFailed}</p>
          <ProblemMessage error={unit.error} />
        </div>
      ) : (
        <ScanArea unit={unit.data} />
      )}

      <AyahSection anchor={review.hedef_anahtar} kapsam={meal.kapsam} />
      {unit.data && !parsed.isAyah && !(meal.follower && unit.data.metin === '') ? (
        <UnitTextSection heading={textHeading} text={unit.data.metin} />
      ) : null}
      {meal.follower ? <FollowerSection headAnchor={meal.headAnchor} /> : null}
      {meal.besmele !== null ? <BasmalaSection besmele={meal.besmele} /> : null}
      <PipelineNotes extras={extras} />
      <ProposalDiff review={review} />

      {unit.data ? <CorrectSection review={review} unit={unit.data} meal={meal} /> : null}
      <section
        aria-label={trOcr.actions.heading}
        className="flex flex-col gap-2"
        data-testid="ocr-closed-actions"
      >
        <h3 className="text-sm font-medium">{trOcr.actions.heading}</h3>
        <div className="flex flex-wrap gap-2">
          <OpenQuestionButton label={trOcr.actions.split} phase="S-15" />
          <OpenQuestionButton label={trOcr.actions.merge} phase="S-15" />
          <OpenQuestionButton label={trOcr.actions.uncertain} phase="S-15" />
          <OpenQuestionButton label={trOcr.actions.note} phase="S-15" />
        </div>
      </section>

      <ApprovalStages review={review} />
      {/* Unit facts are passed in (null while unknown) so the form does not fetch the unit a second time. */}
      <DecisionForm review={review} unit={unit.data ?? null} onDecided={onDecided} />
    </div>
  );
}
