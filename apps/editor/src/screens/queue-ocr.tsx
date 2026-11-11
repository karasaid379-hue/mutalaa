import { tr } from '@/i18n/tr';
import { QueueLayout, type QueueDetailProps } from '@/review/queue-layout';
import { OcrDetail } from './ocr/ocr-detail';

/** Target table and field of the OCR queue: the text of a unit (K-43 madde 4). */
const OCR_FILTER = { hedef_tablo: 'unit', alan: 'metin' } as const;

function renderDetail(props: QueueDetailProps) {
  return <OcrDetail key={props.review.id} {...props} />;
}

/** Route `kuyruk/ocr`: OCR text corrections, loaded lazily (utif2 and the zoom library stay out of the first bundle). */
export function Component() {
  return <QueueLayout title={tr.nav.queueOcr} filter={OCR_FILTER} renderDetail={renderDetail} />;
}
