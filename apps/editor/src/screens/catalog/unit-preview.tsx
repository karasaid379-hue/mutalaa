import type { components } from '@/api/schema';
import { ArabicText } from '@/components/arabic-text';

type UnitListItem = components['schemas']['UnitListItem'];

export function UnitPreview({ unit }: { unit: UnitListItem }) {
  // The text is clipped by the layout (line clamp), never cut in code.
  return unit.kind === 'ayet' ? (
    <ArabicText as="p" className="line-clamp-2 text-base leading-relaxed">
      {unit.metin}
    </ArabicText>
  ) : (
    <p className="line-clamp-2 text-sm break-words whitespace-pre-wrap">{unit.metin}</p>
  );
}
