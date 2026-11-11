import type { ComponentProps } from 'react';

export interface ScrollRegionProps extends Omit<ComponentProps<'pre'>, 'tabIndex' | 'role'> {
  /** Accessible name of the region; it has to differ from the heading of the section around it. */
  label: string;
}

/**
 * A preformatted block that can scroll. A scrollable area has to be reachable by keyboard (WCAG 2.1.1), so it is
 * a focusable named region.
 */
export function ScrollRegion({ label, ...rest }: ScrollRegionProps) {
  return (
    <pre
      {...rest}
      // A scrollable block is the one non-interactive element that must take focus.
      // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex
      tabIndex={0}
      role="region"
      aria-label={label}
    />
  );
}
