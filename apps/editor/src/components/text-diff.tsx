import { ArabicText } from '@/components/arabic-text';
import { trUi } from '@/i18n/tr-ui';
import { diffText } from '@/lib/text-diff';
import { cn } from '@/lib/utils';

export interface TextDiffProps {
  before: string;
  after: string;
  /** Render as Arabic (`lang="ar"`, `dir="rtl"`, Amiri Quran). */
  arabic?: boolean;
  className?: string;
}

/**
 * Word level difference of two texts: removed words are struck through (`del`), added words underlined
 * (`ins`) in the normal text colour on a light tint, and hidden text ("Silinen metin başı", "Eklenen metin
 * başı") names each group for screen readers. The meaning is never colour only. A combining mark never
 * separates from its letter (see lib/text-diff).
 */
export function TextDiff({ before, after, arabic = false, className }: TextDiffProps) {
  const parts = diffText(before, after);
  const body = parts.map((part, index) => {
    if (part.kind === 'removed') {
      return (
        <span key={index}>
          <span className="sr-only">{trUi.diff.removedStart}</span>
          <del className="bg-destructive/10 text-foreground decoration-destructive decoration-2">
            {part.text}
          </del>
          <span className="sr-only">{trUi.diff.removedEnd}</span>
        </span>
      );
    }
    if (part.kind === 'added') {
      return (
        <span key={index}>
          <span className="sr-only">{trUi.diff.addedStart}</span>
          <ins className="bg-success/15 text-foreground underline decoration-success decoration-2 underline-offset-2">
            {part.text}
          </ins>
          <span className="sr-only">{trUi.diff.addedEnd}</span>
        </span>
      );
    }
    return <span key={index}>{part.text}</span>;
  });
  return arabic ? (
    <ArabicText as="p" className={className} data-testid="text-diff">
      {body}
    </ArabicText>
  ) : (
    <p className={cn('whitespace-pre-wrap', className)} data-testid="text-diff">
      {body}
    </p>
  );
}
