import { useId } from 'react';
import { tr } from '@/i18n/tr';

export interface MissingSectionProps {
  /** Section title (Turkish, from tr.ts). */
  title: string;
  /** Stage(s) that will add the data to the API, e.g. 'A18' or 'A18/A20'. */
  phase: string;
}

/** A placeholder for data the API does not provide yet: a heading and the "Bu bilgi API'de henüz yok" note; nothing is invented. */
export function MissingSection({ title, phase }: MissingSectionProps) {
  const headingId = useId();
  return (
    <section aria-labelledby={headingId} className="rounded-lg border border-dashed p-3">
      <h3 id={headingId} className="text-sm font-medium">
        {title}
      </h3>
      <p className="text-sm text-muted-foreground">{tr.missing.section(phase)}</p>
    </section>
  );
}
