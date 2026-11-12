import { useId, type KeyboardEvent } from 'react';
import { useApi } from '@/app/api-context';
import { ArabicText } from '@/components/arabic-text';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { trLemma } from '@/i18n/tr-lemma';
import { fieldA11y, type FieldProblem } from './field-errors';
import { parseIdInput } from './rules';

const LEMMA_PATH = '/api/v1/lemmas/{id}' as const;

export interface RootMappingFieldsProps {
  /** Ids of the two inputs (the error summary links to them). */
  rootFieldId: string;
  arFieldId: string;
  /** Id of the error summary list. */
  summaryId: string;
  problems: readonly FieldProblem[];
  root: string;
  arLemma: string;
  etymologicalOnly: boolean;
  onRoot: (value: string) => void;
  onArLemma: (value: string) => void;
  onEtymologicalOnly: (value: boolean) => void;
  onKeyDown: (event: KeyboardEvent<HTMLElement>) => void;
}

/**
 * The preview of the typed Arabic lemma id (`GET /lemmas/{id}`): the lemma as stored, its root letters and id,
 * and a hint when its root is not the typed root. It only helps the choice; the server has the last word.
 */
function ArLemmaPreview({
  arLemmaId,
  rootId,
  onUseRoot,
}: {
  arLemmaId: number;
  rootId: number | null;
  onUseRoot: (rootId: number) => void;
}) {
  const api = useApi();
  const query = api.$api.useQuery(
    'get',
    LEMMA_PATH,
    { params: { path: { id: arLemmaId } } },
    { retry: false },
  );
  const text = trLemma.kok.edit.preview;
  const data = query.data;
  const kok = data?.kok ?? null;
  return (
    <section
      aria-label={text.heading}
      aria-busy={query.isPending}
      className="flex flex-col gap-1 rounded-lg border p-2 text-sm"
      data-testid="ar-lemma-preview"
    >
      <h4 className="text-xs font-medium">{text.heading}</h4>
      {query.isPending ? (
        <p className="text-muted-foreground">{text.loading}</p>
      ) : query.isError || !data ? (
        <p className="text-muted-foreground">{text.failed}</p>
      ) : data.lemma.lang !== 'ar' ? (
        <p className="font-medium">{text.notArabic}</p>
      ) : (
        <>
          <dl>
            <div className="flex flex-wrap items-baseline gap-x-2">
              <dt className="text-muted-foreground">{text.lemma}</dt>
              <dd>
                <ArabicText text={data.lemma.text} className="text-lg" />
              </dd>
            </div>
            {kok ? (
              <>
                <div className="flex flex-wrap items-baseline gap-x-2">
                  <dt className="text-muted-foreground">{text.root}</dt>
                  <dd>
                    <ArabicText text={kok.letters} className="text-lg" />
                  </dd>
                </div>
                <div className="flex flex-wrap gap-x-2">
                  <dt className="text-muted-foreground">{text.rootId}</dt>
                  <dd>{String(kok.id)}</dd>
                </div>
              </>
            ) : (
              <div>
                <dd>{text.noRoot}</dd>
              </div>
            )}
          </dl>
          {kok && kok.id !== rootId ? (
            <div className="flex flex-col items-start gap-1">
              <p className="font-medium">{text.mismatch(kok.id)}</p>
              <Button type="button" variant="outline" size="sm" onClick={() => onUseRoot(kok.id)}>
                {text.useRoot}
              </Button>
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}

/**
 * The edit fields of "Düzenle ve onayla" for a Turkish lemma mapping (K-51 madde 9): the root id and the
 * optional Arabic lemma id (typed; the API has no root search, so the Arabic lemma preview shows the root to
 * choose) and the "yalnızca etimolojik" switch. The input is kept as typed; the parent validates and sends it.
 */
export function RootMappingFields({
  rootFieldId,
  arFieldId,
  summaryId,
  problems,
  root,
  arLemma,
  etymologicalOnly,
  onRoot,
  onArLemma,
  onEtymologicalOnly,
  onKeyDown,
}: RootMappingFieldsProps) {
  const text = trLemma.kok.edit;
  const rootHintId = useId();
  const arHintId = useId();
  const etymId = useId();
  const parsedAr = parseIdInput(arLemma);
  const parsedRoot = parseIdInput(root);
  return (
    <fieldset className="flex flex-col gap-3 rounded-lg border p-3" data-testid="mapping-edit">
      <legend className="px-1 text-sm font-medium">{text.legend}</legend>
      <p className="text-xs text-muted-foreground">{text.hint}</p>
      <div className="flex flex-col gap-1">
        <Label htmlFor={rootFieldId}>{text.rootId}</Label>
        <Input
          id={rootFieldId}
          inputMode="numeric"
          autoComplete="off"
          dir="ltr"
          value={root}
          onChange={(event) => onRoot(event.target.value)}
          onKeyDown={onKeyDown}
          {...fieldA11y(problems, rootFieldId, summaryId, rootHintId)}
        />
        <p id={rootHintId} className="text-xs text-muted-foreground">
          {text.rootHint}
        </p>
      </div>
      <div className="flex flex-col gap-1">
        <Label htmlFor={arFieldId}>{text.arLemmaId}</Label>
        <Input
          id={arFieldId}
          inputMode="numeric"
          autoComplete="off"
          dir="ltr"
          value={arLemma}
          onChange={(event) => onArLemma(event.target.value)}
          onKeyDown={onKeyDown}
          {...fieldA11y(problems, arFieldId, summaryId, arHintId)}
        />
        <p id={arHintId} className="text-xs text-muted-foreground">
          {text.arHint}
        </p>
      </div>
      {typeof parsedAr === 'number' ? (
        <ArLemmaPreview
          key={parsedAr}
          arLemmaId={parsedAr}
          rootId={typeof parsedRoot === 'number' ? parsedRoot : null}
          onUseRoot={(rootId) => onRoot(String(rootId))}
        />
      ) : null}
      <div className="flex min-h-6 items-center gap-2">
        <Checkbox
          id={etymId}
          checked={etymologicalOnly}
          onCheckedChange={(checked) => onEtymologicalOnly(checked === true)}
        />
        <Label htmlFor={etymId} className="font-normal">
          {text.etymological}
        </Label>
      </div>
    </fieldset>
  );
}
