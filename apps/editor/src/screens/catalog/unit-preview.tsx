import type { components } from '@/api/schema';
import { ArabicText } from '@/components/arabic-text';

type UnitListItem = components['schemas']['UnitListItem'];

export function UnitPreview({ unit }: { unit: UnitListItem }) {
  // The text is clipped by the layout (line clamp), never cut in code. Right to left only for ayah units (the
  // list item has no source kind); Arabic hadith text will need this widened in A19.
  return unit.kind === 'ayet' ? (
    <ArabicText as="p" className="line-clamp-2 text-base leading-relaxed">
      {unit.metin}
    </ArabicText>
  ) : (
    <p dir="auto" className="line-clamp-2 text-sm break-words whitespace-pre-wrap">
      {unit.metin}
    </p>
  );
}
