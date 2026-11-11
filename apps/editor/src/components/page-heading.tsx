import { useEffect, useRef, type ReactNode } from 'react';
import { cn } from '@/lib/utils';

/** The `h1` of a screen. It takes focus once when the screen opens (route change), so keyboard and screen reader users start at the title. */
export function PageHeading({ children, className }: { children: ReactNode; className?: string }) {
  const ref = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    ref.current?.focus();
  }, []);
  return (
    <h1 ref={ref} tabIndex={-1} className={cn('text-xl font-semibold outline-none', className)}>
      {children}
    </h1>
  );
}
