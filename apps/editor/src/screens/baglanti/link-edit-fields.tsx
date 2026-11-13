import { useId, useMemo, useState, type ReactNode } from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { labelOf } from '@/i18n/labels';
import { trBaglanti } from '@/i18n/tr-baglanti-sure';
import type { ExtraEdit } from '@/review/decision-form';
import type { FieldProblem } from '@/review/field-errors';
import type { ReviewDetail } from '@/review/types';
import {
  EDITABLE_TYPES,
  EMPTY_LINK_EDIT,
  isEditableType,
  resolveLinkEdit,
  type LinkEditInput,
} from './link-edit';
import { readSpan } from './link-snapshot';
import { targetInfo } from './target';

/** Value of the "Değiştirme" radio (an empty string is not a usable radio value). */
const KEEP = 'keep';

export interface LinkEditForm {
  /** Passed to `DecisionForm` as `extraEdit`: the approval body and the problems that block it. */
  extraEdit: ExtraEdit;
  /** Passed to `DecisionForm` as `extraFields`. */
  fields: ReactNode;
}

/**
 * The edit fields of a link candidate: "Hedefi değiştir" (target anchor), "Aralığı düzelt" (target span, two
 * integers, half open) and "Tür değiştir" (atıf, iktibas, ima). The fields belong to the decision form: they are
 * sent only with "Onayla" (`duzenlenen`), empty fields change nothing, and the checks follow the server's rules.
 */
export function useLinkEditForm(review: ReviewDetail): LinkEditForm {
  const ids = {
    anchor: useId(),
    anchorHint: useId(),
    anchorError: useId(),
    spanStart: useId(),
    spanEnd: useId(),
    spanHint: useId(),
    spanError: useId(),
    type: useId(),
    summary: useId(),
  };
  const [input, setInput] = useState<LinkEditInput>(EMPTY_LINK_EDIT);
  const [touched, setTouched] = useState({ anchor: false, span: false });
  const target = review.hedef;
  const currentDst = target?.dst_anchor ?? null;
  const currentType = target?.type ?? null;
  const result = useMemo(
    () => resolveLinkEdit(input, { currentType, currentDst }),
    [input, currentType, currentDst],
  );

  const text = trBaglanti.edit;
  const anchorProblem = result.problems.find((problem) => problem.field === 'dstAnchor');
  const spanProblem = result.problems.find((problem) => problem.field === 'span');
  const showAnchorProblem = touched.anchor && anchorProblem !== undefined;
  const showSpanProblem = touched.span && spanProblem !== undefined;
  const typeEditable = isEditableType(currentType);
  const kuran = currentDst !== null && targetInfo(currentDst).ayah;
  const currentSpan = readSpan(target?.dst_span);

  const problems: FieldProblem[] = result.problems.map((problem) => ({
    fieldId: problem.field === 'dstAnchor' ? ids.anchor : ids.spanStart,
    message: text.problems[problem.code],
  }));

  const fields = (
    <fieldset className="flex flex-col gap-3 rounded-lg border p-3" data-testid="link-edit">
      <legend className="px-1 text-sm font-medium">{text.heading}</legend>
      <p className="text-xs text-muted-foreground">{text.hint}</p>

      <div className="flex flex-col gap-1">
        <Label htmlFor={ids.anchor}>{text.target}</Label>
        <Input
          id={ids.anchor}
          dir="ltr"
          value={input.dstAnchor}
          aria-invalid={showAnchorProblem ? true : undefined}
          aria-describedby={
            showAnchorProblem ? `${ids.anchorHint} ${ids.anchorError}` : ids.anchorHint
          }
          onChange={(event) => setInput({ ...input, dstAnchor: event.target.value })}
          onBlur={() => setTouched((previous) => ({ ...previous, anchor: true }))}
        />
        <p id={ids.anchorHint} className="text-xs text-muted-foreground">
          {currentDst === null ? text.targetNone : text.targetHint(currentDst)}
        </p>
        {showAnchorProblem ? (
          <p id={ids.anchorError} className="text-xs font-medium text-destructive">
            {text.problems[anchorProblem.code]}
          </p>
        ) : null}
      </div>

      <fieldset className="flex flex-col gap-1" aria-describedby={ids.spanHint}>
        <legend className="text-sm font-medium">{text.span}</legend>
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex flex-col gap-1">
            <Label htmlFor={ids.spanStart}>{text.spanStart}</Label>
            <Input
              id={ids.spanStart}
              dir="ltr"
              inputMode="numeric"
              className="w-28"
              value={input.spanStart}
              disabled={result.anchorCarriesSpan}
              aria-invalid={showSpanProblem ? true : undefined}
              aria-describedby={showSpanProblem ? ids.spanError : undefined}
              onChange={(event) => setInput({ ...input, spanStart: event.target.value })}
              onBlur={() => setTouched((previous) => ({ ...previous, span: true }))}
            />
          </div>
          <div className="flex flex-col gap-1">
            <Label htmlFor={ids.spanEnd}>{text.spanEnd}</Label>
            <Input
              id={ids.spanEnd}
              dir="ltr"
              inputMode="numeric"
              className="w-28"
              value={input.spanEnd}
              disabled={result.anchorCarriesSpan}
              aria-invalid={showSpanProblem ? true : undefined}
              aria-describedby={showSpanProblem ? ids.spanError : undefined}
              onChange={(event) => setInput({ ...input, spanEnd: event.target.value })}
              onBlur={() => setTouched((previous) => ({ ...previous, span: true }))}
            />
          </div>
        </div>
        <p id={ids.spanHint} className="text-xs text-muted-foreground">
          {[
            text.spanHint,
            kuran ? text.spanKuran : text.spanText,
            currentSpan !== null
              ? text.spanCurrent(trBaglanti.evidence.spanValue(currentSpan[0], currentSpan[1]))
              : null,
            result.anchorCarriesSpan ? text.spanCarried : null,
          ]
            .filter((part): part is string => part !== null)
            .join(' ')}
        </p>
        {showSpanProblem ? (
          <p id={ids.spanError} className="text-xs font-medium text-destructive">
            {text.problems[spanProblem.code]}
          </p>
        ) : null}
      </fieldset>

      {typeEditable ? (
        <RadioGroup
          id={ids.type}
          aria-label={text.type}
          value={input.type === '' ? KEEP : input.type}
          className="flex flex-wrap items-center gap-x-4 gap-y-1"
          onValueChange={(next) => {
            if (next === KEEP) setInput({ ...input, type: '' });
            else if (isEditableType(next)) setInput({ ...input, type: next });
          }}
        >
          <span className="text-sm font-medium" aria-hidden="true">
            {text.type}
          </span>
          <Label className="min-h-6 gap-2 font-normal">
            <RadioGroupItem value={KEEP} />
            {text.typeKeep}
          </Label>
          {EDITABLE_TYPES.filter((type) => type !== currentType).map((type) => (
            <Label key={type} className="min-h-6 gap-2 font-normal">
              <RadioGroupItem value={type} />
              {labelOf(trBaglanti.types, type)}
            </Label>
          ))}
        </RadioGroup>
      ) : (
        <p className="text-xs text-muted-foreground">{text.typeLocked}</p>
      )}
      {typeEditable ? (
        <p className="text-xs text-muted-foreground">
          {text.typeCurrent(labelOf(trBaglanti.types, currentType))}
        </p>
      ) : null}
    </fieldset>
  );

  return { extraEdit: { value: result.value, problems }, fields };
}
