import { ArabicText } from '@/components/arabic-text';
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
 * (`ins`). The marks are not colour only. A combining mark never separates from its letter (see lib/text-diff).
 */
export function TextDiff({ before, after, arabic = false, className }: TextDiffProps) {
  const parts = diffText(before, after);
  const body = parts.map((part, index) => {
    if (part.kind === 'removed') {
      return (
        <del key={index} className="bg-destructive/10 text-destructive">
          {part.text}
        </del>
      );
    }
    if (part.kind === 'added') {
      return (
        <ins
          key={index}
          className="bg-green-100 text-green-900 dark:bg-green-900/30 dark:text-green-100"
        >
          {part.text}
        </ins>
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
