import { useId } from 'react';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { trOcr } from '@/i18n/tr-ocr';
import {
  OCR_SOURCE_TABS,
  OCR_STAGE_VIEWS,
  isOcrSourceTab,
  isOcrStageView,
  type OcrSourceTab,
  type OcrStageView,
} from './config';
import { MEAL_SOURCE_SLUG } from './meal-source';

export interface OcrFiltersProps {
  source: OcrSourceTab;
  stage: OcrStageView;
  onSourceChange: (value: OcrSourceTab) => void;
  onStageChange: (value: OcrStageView) => void;
}

/** A tab row without panels: the tabs filter the list beside them, so there is no tab panel to point at. */
const TAB_LIST_CLASS = 'h-auto w-full flex-wrap group-data-horizontal/tabs:h-auto';
const TAB_CLASS = 'min-h-6 py-1';

/**
 * The two tab rows above the OCR list: the source (every source, original meal, simplified meal) and the approval
 * stage (all, first approval pending, second approval pending). The tabs filter the list, they do not switch
 * panels: there is no tab panel (so no empty focus stop), the explanation of the selected tab is plain text tied to
 * the row with `aria-describedby`. The parent keeps the selection (the URL) and drops `?kayit=` on a change.
 */
export function OcrFilters({ source, stage, onSourceChange, onStageChange }: OcrFiltersProps) {
  const sourceHintId = useId();
  const stageHintId = useId();
  return (
    <div className="flex flex-col gap-3" data-testid="ocr-filters">
      <div className="flex flex-col gap-2">
        <Tabs
          value={source}
          onValueChange={(next) => {
            if (isOcrSourceTab(next) && next !== source) onSourceChange(next);
          }}
        >
          <TabsList
            aria-label={trOcr.filters.sourceLabel}
            aria-describedby={sourceHintId}
            className={TAB_LIST_CLASS}
          >
            {OCR_SOURCE_TABS.map((id) => (
              <TabsTrigger key={id} value={id} className={TAB_CLASS}>
                {trOcr.filters.sources[id]}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
        <p id={sourceHintId} className="text-xs text-muted-foreground">
          {trOcr.filters.sourceHints[source]}
          {source !== 'hepsi' ? (
            <>
              {' '}
              {trOcr.filters.sourceIdLabel}{' '}
              <code className="break-all">{MEAL_SOURCE_SLUG[source]}</code>
            </>
          ) : null}
        </p>
      </div>
      <div className="flex flex-col gap-2">
        <Tabs
          value={stage}
          onValueChange={(next) => {
            if (isOcrStageView(next) && next !== stage) onStageChange(next);
          }}
        >
          <TabsList
            aria-label={trOcr.filters.stageLabel}
            aria-describedby={stageHintId}
            className={TAB_LIST_CLASS}
          >
            {OCR_STAGE_VIEWS.map((id) => (
              <TabsTrigger key={id} value={id} className={TAB_CLASS}>
                {trOcr.filters.stages[id]}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
        <p id={stageHintId} className="text-xs text-muted-foreground">
          {trOcr.filters.stageHints[stage]}
        </p>
      </div>
    </div>
  );
}
