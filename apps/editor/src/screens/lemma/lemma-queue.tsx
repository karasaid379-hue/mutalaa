import { useId, useState } from 'react';
import { useSearchParams } from 'react-router';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { fieldLabel } from '@/i18n/labels';
import { tr } from '@/i18n/tr';
import { trLemma } from '@/i18n/tr-lemma';
import { formatPercent } from '@/lib/format';
import type { QueueOrder } from '@/review/queries';
import { QueueLayout } from '@/review/queue-layout';
import type { ReviewItem } from '@/review/types';
import {
  DEFAULT_LEMMA_ORDER,
  LEMMA_ORDERS,
  LEMMA_TAB_IDS,
  hasWaveOrder,
  isLemmaTab,
  isQueueOrder,
  lemmaFilter,
  type LemmaTabId,
} from './config';
import { LemmaCard } from './lemma-card';
import { consistencyOf, readConfidence } from './payload';
import { WordFixCard } from './word-fix-card';

interface LemmaTabsProps {
  value: LemmaTabId;
  onChange: (value: LemmaTabId) => void;
}

/** The queue tabs. A record of the other tab is not shown, so the selection (`?kayit=`) is dropped on change. */
function LemmaTabs({ value, onChange }: LemmaTabsProps) {
  const [, setParams] = useSearchParams();
  return (
    <Tabs
      value={value}
      onValueChange={(next) => {
        if (!isLemmaTab(next) || next === value) return;
        setParams({}, { replace: true });
        onChange(next);
      }}
    >
      <TabsList aria-label={trLemma.tabsLabel} className="h-auto w-full flex-wrap">
        {LEMMA_TAB_IDS.map((id) => (
          <TabsTrigger key={id} value={id} className="min-h-6">
            {trLemma.tabs[id]}
          </TabsTrigger>
        ))}
      </TabsList>
      {LEMMA_TAB_IDS.map((id) => (
        <TabsContent key={id} value={id}>
          <p className="text-xs text-muted-foreground">{trLemma.tabHints[id]}</p>
        </TabsContent>
      ))}
    </Tabs>
  );
}

interface OrderControlProps {
  value: QueueOrder;
  onChange: (value: QueueOrder) => void;
}

/** "Sıra: Dalga | Oluşturma": the wave and root order of the editorial work, or the creation order. */
function OrderControl({ value, onChange }: OrderControlProps) {
  const hintId = useId();
  return (
    <div className="flex flex-col gap-1" data-testid="lemma-order">
      <RadioGroup
        aria-label={trLemma.order.label}
        aria-describedby={hintId}
        value={value}
        className="flex flex-wrap items-center gap-x-4 gap-y-1"
        onValueChange={(next) => {
          if (isQueueOrder(next)) onChange(next);
        }}
      >
        <span className="text-sm font-medium" aria-hidden="true">
          {trLemma.order.label}
        </span>
        {LEMMA_ORDERS.map((order) => (
          <Label key={order} className="min-h-6 gap-2 font-normal">
            <RadioGroupItem value={order} />
            {trLemma.order[order]}
          </Label>
        ))}
      </RadioGroup>
      <p id={hintId} className="text-xs text-muted-foreground">
        {trLemma.order.hint}
      </p>
    </div>
  );
}

/** Under a word meaning candidate in the list: the consistent or inconsistent mark of its dominant share. */
function GlossMeta({ item }: { item: ReviewItem }) {
  if (item.hedef_tablo === 'quran_word_fix') {
    return (
      <span className="text-xs text-muted-foreground">
        {trLemma.list.fix(fieldLabel(item.alan))}
      </span>
    );
  }
  const share = item.hedef_tablo === 'lemma_gloss' ? readConfidence(item) : null;
  if (share === null) return null;
  return (
    <span className="text-xs text-muted-foreground" data-testid="lemma-item-consistency">
      {trLemma.list.line(
        consistencyOf(share) === 'tutarli' ? trLemma.list.consistent : trLemma.list.inconsistent,
        formatPercent(share),
      )}
    </span>
  );
}

/**
 * Route `kuyruk/lemma` (Kelime anlamları §6, K-13): the word meaning drafts (`lemma_gloss` + `anlam_kisa`),
 * the lemma status (`lemma` + `status`) and the root and lemma corrections (`quran_word_fix`, every field) on
 * three tabs; the filter is screen state. The first two are listed in wave order (`sira=dalga`, the default)
 * or in creation order; changing the order is a new query, so the cursor starts over (the API's cursors are
 * typed by order). The correction tab has no order (the API answers 400).
 */
export function LemmaQueue() {
  const [tab, setTab] = useState<LemmaTabId>('anlam');
  const [order, setOrder] = useState<QueueOrder>(DEFAULT_LEMMA_ORDER);
  return (
    <QueueLayout
      title={tr.nav.queueLemma}
      filter={lemmaFilter(tab, order)}
      announceCount
      renderListHeader={() => (
        <div className="flex flex-col gap-3">
          <LemmaTabs value={tab} onChange={setTab} />
          {hasWaveOrder(tab) ? <OrderControl value={order} onChange={setOrder} /> : null}
        </div>
      )}
      renderItemMeta={(item) => <GlossMeta item={item} />}
      renderDetail={({ review, onDecided }) =>
        review.hedef_tablo === 'quran_word_fix' ? (
          <WordFixCard key={review.id} review={review} onDecided={onDecided} />
        ) : (
          <LemmaCard key={review.id} review={review} onDecided={onDecided} />
        )
      }
    />
  );
}
