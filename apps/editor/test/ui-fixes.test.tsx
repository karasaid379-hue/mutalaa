// A15 review fixes, part 2: one live region, reflowing navigation, hidden explanations instead of titles,
// text differences that do not rely on colour, decorative spinner and busy loading states.
import { act, render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { OpenQuestionButton } from '@/components/open-question-button';
import { TextDiff } from '@/components/text-diff';
import { Skeleton } from '@/components/ui/skeleton';
import { Toaster, toast } from '@/components/ui/toast';
import { Spinner } from '@/components/ui/spinner';
import { tr } from '@/i18n/tr';
import { trUi } from '@/i18n/tr-ui';
import { ReviewBadges } from '@/review/badges';
import { useFakeApi } from './fake-api';
import { reviewDetail, signedIn } from './fixtures';
import { renderApp } from './render-app';

describe('one live region', () => {
  const fake = useFakeApi();

  it.each([
    ['/kuyruk/ocr', 'queue-empty'],
    ['/kaynaklar', 'sources-empty'],
    ['/birimler', 'units-empty'],
    ['/yayinlar', 'releases-empty'],
  ] as const)('%s has one status region and no toast region', async (path, testId) => {
    signedIn(fake);
    renderApp(fake, path);
    await screen.findByTestId(testId);
    expect(document.querySelectorAll('[role="status"]')).toHaveLength(1);
    expect(document.querySelectorAll('[aria-live]')).toHaveLength(1);
    expect(screen.queryByLabelText('Notifications')).toBeNull();
  });

  it('a toast region, when one is mounted, has a Turkish name', async () => {
    render(<Toaster />);
    act(() => {
      toast.add({ title: 'Deneme bildirimi' });
    });
    expect(await screen.findByText('Deneme bildirimi')).toBeInTheDocument();
    expect(document.querySelector('[data-slot=toast-viewport]')).toHaveAttribute(
      'aria-label',
      trUi.toastRegion,
    );
    expect(screen.queryByLabelText('Notifications')).toBeNull();
  });

  it('the spinner is decorative and the skeleton is hidden from assistive technology', () => {
    const { container } = render(
      <div>
        <Spinner />
        <Skeleton className="h-4" />
      </div>,
    );
    expect(container.querySelector('[data-slot="spinner"]')).toHaveAttribute('aria-hidden', 'true');
    expect(container.querySelector('[data-slot="spinner"]')).not.toHaveAttribute('role');
    expect(container.querySelector('[data-slot="skeleton"]')).toHaveAttribute(
      'aria-hidden',
      'true',
    );
    expect(screen.queryByRole('status')).toBeNull();
  });
});

describe('navigation reflow', () => {
  const fake = useFakeApi();

  it('stacks above the page below lg and is the 14rem column from lg', async () => {
    signedIn(fake);
    renderApp(fake, '/kaynaklar');
    const nav = await screen.findByRole('navigation', { name: tr.nav.label });
    const classes = nav.className.split(/\s+/);
    expect(classes).toContain('w-full');
    expect(classes).toContain('lg:w-56');
    expect(classes).not.toContain('w-56');
    expect(classes).toContain('lg:border-r');
    for (const list of Array.from(nav.querySelectorAll('ul'))) {
      expect(list.className).toContain('flex-wrap');
      expect(list.className).toContain('lg:flex-col');
    }
    expect(nav.parentElement).toHaveClass('flex-col', 'lg:flex-row');
  });

  it('gives every navigation link a visible focus ring', async () => {
    signedIn(fake);
    renderApp(fake, '/kaynaklar');
    const nav = await screen.findByRole('navigation', { name: tr.nav.label });
    const links = within(nav).getAllByRole('link');
    expect(links.length).toBeGreaterThan(0);
    for (const link of links)
      expect(link).toHaveClass('focus-visible:ring-2', 'focus-visible:ring-ring');
  });
});

describe('hidden explanations', () => {
  it('the unverified badge is tied to its explanation and has no title', () => {
    render(<ReviewBadges review={reviewDetail({ dogrulanmamis: true })} />);
    const badge = screen.getByText(tr.badge.unverified);
    expect(badge).not.toHaveAttribute('title');
    expect(badge).toHaveAccessibleDescription(tr.badge.unverifiedHint);
  });

  it('the open question button is described by hidden text, has no title and no pressed movement', () => {
    render(<OpenQuestionButton label="Böl" phase="S-15" />);
    const button = screen.getByRole('button');
    expect(button).not.toHaveAttribute('title');
    expect(button).toHaveAccessibleDescription(tr.openQuestionHint);
    expect(button.className).toContain('not-aria-disabled:translate-y-px');
    expect(button.className).toContain('cursor-not-allowed');
  });
});

describe('text difference without colour', () => {
  it('names removed and added groups for screen readers and keeps the marks', () => {
    render(<TextDiff before="Deneme paragrafı 1" after="Deneme paragrafı 2" />);
    const diff = screen.getByTestId('text-diff');
    expect(diff.querySelector('del')).toHaveTextContent('1');
    expect(diff.querySelector('ins')).toHaveTextContent('2');
    expect(diff.textContent).toBe(
      `Deneme paragrafı ${trUi.diff.removedStart}1${trUi.diff.removedEnd}${trUi.diff.addedStart}2${trUi.diff.addedEnd}`,
    );
    for (const hidden of Array.from(diff.querySelectorAll('.sr-only'))) {
      expect(hidden.closest('del, ins')).toBeNull();
    }
    // No fixed colour palette: tokens only.
    expect(diff.innerHTML).not.toMatch(/green-|red-/);
    expect(diff.querySelector('ins')?.className).toContain('text-foreground');
    expect(diff.querySelector('del')?.className).toContain('text-foreground');
  });
});

describe('loading states', () => {
  const fake = useFakeApi();

  it.each([
    ['/kaynaklar', '/api/v1/sources', 'sources-loading'],
    ['/birimler', '/api/v1/units', 'units-loading'],
    ['/yayinlar', '/api/v1/releases', 'releases-loading'],
  ] as const)('%s is busy and says so in hidden text', async (path, api, testId) => {
    signedIn(fake);
    fake.get(api, () => new Promise(() => undefined));
    renderApp(fake, path);
    const loading = await screen.findByTestId(testId);
    expect(loading).toHaveAttribute('aria-busy', 'true');
    expect(within(loading).getByText(tr.ui.loading)).toHaveClass('sr-only');
    expect(document.querySelectorAll('[role="status"]')).toHaveLength(1);
  });
});
