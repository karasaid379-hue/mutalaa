import { Badge } from '@/components/ui/badge';
import { trOcr } from '@/i18n/tr-ocr';
import { mealEditionOf } from './meal-source';

/**
 * The source of a meal unit: its name and the edition label ("orijinal" or "sadeleştirilmiş", K-49 madde 1).
 * Nothing is drawn for an anchor that is not one of the two Elmalılı meals. The edition comes from the anchor's
 * meal id (`elmalili`, `elmalili-sade`), which is fixed per source.
 */
export function SourceLine({ anchor }: { anchor: string }) {
  const edition = mealEditionOf(anchor);
  if (edition === null) return null;
  return (
    <span className="flex flex-wrap items-center gap-1 text-sm" data-testid="ocr-source">
      <span className="text-muted-foreground">{trOcr.source.label}</span>
      <span>{trOcr.source.names[edition]}</span>
      <Badge variant="outline">{trOcr.source.editions[edition]}</Badge>
    </span>
  );
}
