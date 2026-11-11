import type { ComponentProps, ReactNode } from 'react';
import { cn } from '@/lib/utils';

export interface ArabicTextProps extends Omit<
  ComponentProps<'span'>,
  'children' | 'lang' | 'dir' | 'ref'
> {
  /** The text exactly as stored: it is rendered as is (no trim, no normalization; K-26). */
  text?: string;
  /** Rich content (for example diff parts) instead of `text`; the same attributes apply. */
  children?: ReactNode;
  as?: 'span' | 'p' | 'div';
}

/**
 * The only place that renders Arabic with the Amiri Quran font (`font-quran`). `lang="ar"` and
 * `dir="rtl"` are always set; the text is never changed. Whitespace is kept visible as stored.
 */
export function ArabicText({
  text,
  children,
  as: Tag = 'span',
  className,
  ...rest
}: ArabicTextProps) {
  return (
    <Tag
      {...rest}
      lang="ar"
      dir="rtl"
      className={cn('font-quran text-2xl leading-loose whitespace-pre-wrap', className)}
    >
      {children ?? text}
    </Tag>
  );
}
