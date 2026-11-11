import { useState } from 'react';
import { useSearchParams } from 'react-router';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { tr } from '@/i18n/tr';
import { trLemma } from '@/i18n/tr-lemma';
import { QueueLayout } from '@/review/queue-layout';
import { LEMMA_FILTERS, LEMMA_TAB_IDS, isLemmaTab, type LemmaTabId } from './config';
import { LemmaCard } from './lemma-card';

interface LemmaTabsProps {
  value: LemmaTabId;
  onChange: (value: LemmaTabId) => void;
}

/** The two queue tabs. A record of the other tab is not shown, so the selection (`?kayit=`) is dropped on change. */
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
      <TabsList aria-label={trLemma.tabsLabel} className="h-auto w-full">
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

/**
 * Route `kuyruk/lemma` (Kelime anlamları §6): the word meaning drafts (`lemma_gloss` + `anlam_kisa`) and the
 * lemma status (`lemma` + `status`) on two tabs; the filter is screen state. The list is `created_at, id`
 * ordered (wave and root order are not in the API yet, A17).
 */
export function LemmaQueue() {
  const [tab, setTab] = useState<LemmaTabId>('anlam');
  return (
    <QueueLayout
      title={tr.nav.queueLemma}
      filter={LEMMA_FILTERS[tab]}
      renderListHeader={() => <LemmaTabs value={tab} onChange={setTab} />}
      renderDetail={({ review, onDecided }) => (
        <LemmaCard key={review.id} review={review} onDecided={onDecided} />
      )}
    />
  );
}
