import { useMemo } from 'react';
import { useSearchParams } from 'react-router';
import { tr } from '@/i18n/tr';
import { QueueLayout, type QueueDetailProps } from '@/review/queue-layout';
import {
  isOcrSourceTab,
  isOcrStageView,
  ocrFilter,
  type OcrSourceTab,
  type OcrStageView,
} from './ocr/config';
import { OcrDetail } from './ocr/ocr-detail';
import { OcrFilters } from './ocr/ocr-filters';
import { SourceLine } from './ocr/source-line';

/** URL parameters of the two tab rows; the default tab ("hepsi") leaves its parameter out. */
const SOURCE_PARAM = 'kaynak';
const STAGE_PARAM = 'asama';
const RECORD_PARAM = 'kayit';

function renderDetail(props: QueueDetailProps) {
  return <OcrDetail key={props.review.id} {...props} />;
}

/**
 * Route `kuyruk/ocr`: unit text corrections and the two Elmalılı meals (K-49), loaded lazily (utif2 and the zoom
 * library stay out of the first bundle). The source tab and the stage view live in the URL (`?kaynak=`, `?asama=`,
 * so a reload or the back button keeps them) and become the `kaynak` and `asama` parameters of the list. A change
 * drops only `?kayit=`: a record of another view is not in the list.
 */
export function Component() {
  const [params, setParams] = useSearchParams();
  const rawSource = params.get(SOURCE_PARAM);
  const rawStage = params.get(STAGE_PARAM);
  const source: OcrSourceTab = isOcrSourceTab(rawSource) ? rawSource : 'hepsi';
  const stage: OcrStageView = isOcrStageView(rawStage) ? rawStage : 'hepsi';
  const filter = useMemo(() => ocrFilter(source, stage), [source, stage]);

  function change(key: string, value: string) {
    setParams(
      (previous) => {
        const next = new URLSearchParams(previous);
        next.delete(RECORD_PARAM);
        if (value === 'hepsi') next.delete(key);
        else next.set(key, value);
        return next;
      },
      { replace: true },
    );
  }

  return (
    <QueueLayout
      title={tr.nav.queueOcr}
      filter={filter}
      announceCount
      renderListHeader={() => (
        <OcrFilters
          source={source}
          stage={stage}
          onSourceChange={(value) => change(SOURCE_PARAM, value)}
          onStageChange={(value) => change(STAGE_PARAM, value)}
        />
      )}
      renderItemMeta={(item) => <SourceLine anchor={item.hedef_anahtar} />}
      renderDetail={renderDetail}
    />
  );
}
