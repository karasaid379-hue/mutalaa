// A18 review fixes on the lemma queue: the objection, the "yalnızca etimolojik" mark and the word fix are shown to
// the Editor policy roles only (the expert gets a note), their forms move focus and announce errors, and the KWIC
// lines have keys of their own.
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import axe from 'axe-core';
import { describe, expect, it, vi } from 'vitest';
import type { components } from '@/api/schema';
import { tr } from '@/i18n/tr';
import { trLemma } from '@/i18n/tr-lemma';
import { LemmaQueue } from '@/screens/lemma/lemma-queue';
import { ok, problem, useFakeApi } from './fake-api';
import { page, session } from './fixtures';
import {
  TR_KWIC,
  glossItem,
  kokDetail,
  kokItem,
  lemmaHandlers,
  lemmaInfo,
  trTarget,
} from './fixtures-lemma';
import { renderInRouter } from './render-app';

type Detail = components['schemas']['ReviewDetailDto'];

async function violations(container: Element): Promise<string[]> {
  const result = await axe.run(container, {
    rules: { 'color-contrast': { enabled: false }, 'target-size': { enabled: false } },
  });
  return result.violations.map((violation) => violation.id);
}

describe('lemma queue: A18 review fixes', () => {
  const fake = useFakeApi();

  const autoDetail = (over: Partial<components['schemas']['ReviewTargetSnapshot']> = {}) =>
    kokDetail(4, { hedef: trTarget(4, { status: 'onayli', onay_yolu: 'otomatik', ...over }) });

  /** The Turkish root mapping tab on record 4 (an automatic approval), or the word meaning tab on record 1. */
  function setupKok(opts: { roles?: string[]; detail?: Detail } = {}) {
    const detail = opts.detail ?? autoDetail();
    fake.get('/api/v1/reviews', (call) =>
      ok(page(call.search.get('alan') === 'kok_eslemesi' ? [kokItem(4)] : [])),
    );
    fake.get('/api/v1/reviews/{id}', ok(detail));
    fake.get('/api/v1/lemmas/{id}', ok(lemmaInfo()));
    fake.get('/api/v1/auth/me', ok(session(opts.roles ?? ['editor'])));
    return renderInRouter(fake, <LemmaQueue />, '/?kayit=4');
  }

  function setupGloss(roles: string[] = ['editor']) {
    fake.get('/api/v1/reviews', ok(page([glossItem(1), glossItem(2)])));
    lemmaHandlers(fake);
    fake.get('/api/v1/auth/me', ok(session(roles)));
    return renderInRouter(fake, <LemmaQueue />, '/?kayit=1');
  }

  describe('the roles', () => {
    it.each([[['editor']], [['admin']], [['editor', 'admin']]])(
      'shows the objection and the etymology mark to the roles %j',
      async (roles) => {
        setupKok({ roles });
        expect(
          await screen.findByRole('button', { name: trLemma.kok.objection.open }),
        ).toBeInTheDocument();
        expect(
          await screen.findByRole('checkbox', { name: trLemma.kok.etym.checkbox }),
        ).toBeInTheDocument();
        expect(screen.queryByTestId('lemma-objection-role-note')).not.toBeInTheDocument();
        expect(screen.queryByTestId('lemma-etymology-role-note')).not.toBeInTheDocument();
      },
    );

    it('tells the expert role that the objection and the mark need the editor role, and shows no form', async () => {
      setupKok({ roles: ['uzman'] });
      const objection = await screen.findByTestId('lemma-objection-role-note');
      const etymology = await screen.findByTestId('lemma-etymology-role-note');
      for (const note of [objection, etymology]) {
        expect(note).toHaveTextContent(tr.review.editorActionNote);
      }
      expect(
        within(objection).getByRole('heading', { level: 3, name: trLemma.kok.objection.heading }),
      ).toBeInTheDocument();
      expect(
        within(etymology).getByRole('heading', { level: 3, name: trLemma.kok.etym.heading }),
      ).toBeInTheDocument();
      expect(
        screen.queryByRole('button', { name: trLemma.kok.objection.open }),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole('checkbox', { name: trLemma.kok.etym.checkbox }),
      ).not.toBeInTheDocument();
      expect(screen.queryByTestId('lemma-objection')).not.toBeInTheDocument();
      expect(screen.queryByTestId('lemma-etymology')).not.toBeInTheDocument();
    });

    it.each([[['editor']], [['admin']]])(
      'shows the word fix form to the roles %j',
      async (roles) => {
        setupGloss(roles);
        expect(
          await screen.findByRole('button', { name: trLemma.wordFixCreate.open }),
        ).toBeInTheDocument();
        expect(screen.queryByTestId('word-fix-create-role-note')).not.toBeInTheDocument();
      },
    );

    it('tells the expert role that the word fix needs the editor role', async () => {
      setupGloss(['uzman']);
      const note = await screen.findByTestId('word-fix-create-role-note');
      expect(note).toHaveTextContent(tr.review.editorActionNote);
      expect(
        within(note).getByRole('heading', { level: 3, name: trLemma.wordFixCreate.heading }),
      ).toBeInTheDocument();
      expect(
        screen.queryByRole('button', { name: trLemma.wordFixCreate.open }),
      ).not.toBeInTheDocument();
    });

    it('shows nothing of these actions while the session is unknown', async () => {
      fake.get('/api/v1/reviews', ok(page([glossItem(1)])));
      lemmaHandlers(fake);
      fake.get('/api/v1/auth/me', () => new Promise(() => undefined));
      renderInRouter(fake, <LemmaQueue />, '/?kayit=1');
      await screen.findByTestId('lemma-card');
      expect(screen.queryByTestId('word-fix-create')).not.toBeInTheDocument();
      expect(screen.queryByTestId('word-fix-create-role-note')).not.toBeInTheDocument();
    });
  });

  describe('the objection form: focus and errors', () => {
    const open = async (user: ReturnType<typeof setupKok>['user']) => {
      await user.click(await screen.findByRole('button', { name: trLemma.kok.objection.open }));
      return screen.getByTestId('lemma-objection');
    };

    it('focuses the reason when the form opens', async () => {
      const { user } = setupKok();
      const box = await open(user);
      expect(within(box).getByLabelText(trLemma.kok.objection.reason)).toHaveFocus();
    });

    it('shows an alert for a missing reason, focuses it, and the link focuses the field', async () => {
      const { user } = setupKok();
      const box = await open(user);
      await user.click(within(box).getByRole('button', { name: trLemma.kok.objection.submit }));
      const alert = await within(box).findByRole('alert');
      expect(alert).toHaveTextContent(trLemma.kok.objection.summaryTitle);
      expect(within(alert).getAllByText(trLemma.kok.objection.reasonRequired)).toHaveLength(1);
      expect(alert.parentElement).toHaveFocus();
      await user.click(
        within(alert).getByRole('link', { name: trLemma.kok.objection.reasonRequired }),
      );
      expect(within(box).getByLabelText(trLemma.kok.objection.reason)).toHaveFocus();
    });

    it('focuses the error of a refused send and keeps the reason', async () => {
      fake.post('/api/v1/lemmas/{id}/itiraz', problem(409, 'durum-gecisi-gecersiz'));
      const { user } = setupKok();
      const box = await open(user);
      fireEvent.change(within(box).getByLabelText(trLemma.kok.objection.reason), {
        target: { value: 'Katılmıyorum' },
      });
      await user.click(within(box).getByRole('button', { name: trLemma.kok.objection.submit }));
      const error = await within(box).findByTestId('objection-error');
      expect(error.parentElement).toHaveFocus();
      expect(within(box).getByLabelText(trLemma.kok.objection.reason)).toHaveValue('Katılmıyorum');
    });

    it('focuses the heading after a success and gives focus back to the button after "Vazgeç"', async () => {
      fake.post('/api/v1/lemmas/{id}/itiraz', ok({ id: 77, durum: 'acik' }, 201));
      const { user } = setupKok();
      let box = await open(user);
      await user.click(within(box).getByRole('button', { name: trLemma.kok.objection.cancel }));
      box = screen.getByTestId('lemma-objection');
      const reopen = within(box).getByRole('button', { name: trLemma.kok.objection.open });
      expect(reopen).toHaveFocus();
      await user.click(reopen);
      fireEvent.change(within(box).getByLabelText(trLemma.kok.objection.reason), {
        target: { value: 'Katılmıyorum' },
      });
      await user.click(within(box).getByRole('button', { name: trLemma.kok.objection.submit }));
      await screen.findByTestId('objection-done');
      await waitFor(() =>
        expect(
          within(screen.getByTestId('lemma-objection')).getByRole('heading', {
            level: 3,
            name: trLemma.kok.objection.heading,
          }),
        ).toHaveFocus(),
      );
    });
  });

  describe('the etymology mark: focus and errors', () => {
    it('focuses the alert of an unchanged value, ties the checkbox to it, and the link focuses the checkbox', async () => {
      const { user } = setupKok();
      const box = await screen.findByTestId('lemma-etymology');
      await user.click(within(box).getByRole('button', { name: trLemma.kok.etym.submit }));
      const alert = await within(box).findByRole('alert');
      expect(alert.parentElement).toHaveFocus();
      const checkbox = within(box).getByRole('checkbox', { name: trLemma.kok.etym.checkbox });
      expect(checkbox).toHaveAttribute('aria-invalid', 'true');
      await user.click(within(alert).getByRole('link', { name: trLemma.kok.etym.unchanged }));
      expect(checkbox).toHaveFocus();
    });

    it('focuses the alert of a missing reason and the link focuses the reason field', async () => {
      const { user } = setupKok();
      const box = await screen.findByTestId('lemma-etymology');
      await user.click(within(box).getByRole('checkbox', { name: trLemma.kok.etym.checkbox }));
      await user.click(within(box).getByRole('button', { name: trLemma.kok.etym.submit }));
      const alert = await within(box).findByRole('alert');
      expect(alert.parentElement).toHaveFocus();
      await user.click(within(alert).getByRole('link', { name: trLemma.kok.etym.reasonRequired }));
      expect(within(box).getByLabelText(trLemma.kok.etym.reason)).toHaveFocus();
    });

    it('focuses the error of a refused send, and the heading after a success', async () => {
      fake.post('/api/v1/lemmas/{id}/etimolojik-isaret', problem(409, 'durum-gecisi-gecersiz'));
      const { user } = setupKok();
      const box = await screen.findByTestId('lemma-etymology');
      await user.click(within(box).getByRole('checkbox', { name: trLemma.kok.etym.checkbox }));
      fireEvent.change(within(box).getByLabelText(trLemma.kok.etym.reason), {
        target: { value: 'Kök yalnız köken' },
      });
      await user.click(within(box).getByRole('button', { name: trLemma.kok.etym.submit }));
      const error = await within(box).findByTestId('etymology-error');
      expect(error.parentElement).toHaveFocus();

      fake.post(
        '/api/v1/lemmas/{id}/etimolojik-isaret',
        ok({ review_id: 88, etymological_only: true, onay_yolu: 'editor', status: 'onayli' }),
      );
      await user.click(within(box).getByRole('button', { name: trLemma.kok.etym.submit }));
      await within(box).findByTestId('etymology-saved');
      await waitFor(() =>
        expect(
          within(screen.getByTestId('lemma-etymology')).getByRole('heading', {
            level: 3,
            name: trLemma.kok.etym.heading,
          }),
        ).toHaveFocus(),
      );
    });
  });

  describe('the word fix form: focus and errors', () => {
    const open = async (user: ReturnType<typeof setupGloss>['user']) => {
      await user.click(await screen.findByRole('button', { name: trLemma.wordFixCreate.open }));
      return screen.getByTestId('word-fix-create');
    };

    it('focuses the anchor field when the form opens', async () => {
      const { user } = setupGloss();
      const box = await open(user);
      expect(within(box).getByLabelText(trLemma.wordFixCreate.anchor)).toHaveFocus();
    });

    it('focuses the alert of the problems, which link to their fields', async () => {
      const { user } = setupGloss();
      const box = await open(user);
      await user.click(within(box).getByRole('button', { name: trLemma.wordFixCreate.submit }));
      const summary = await within(box).findByTestId('word-fix-summary');
      expect(summary).toHaveAttribute('role', 'alert');
      expect(summary.parentElement).toHaveFocus();
      await user.click(
        within(summary).getByRole('link', { name: trLemma.wordFixCreate.problems.valueEmpty }),
      );
      expect(within(box).getByLabelText(trLemma.wordFixCreate.value)).toHaveFocus();
      await user.click(
        within(summary).getByRole('link', { name: trLemma.wordFixCreate.reasonRequired }),
      );
      expect(within(box).getByLabelText(trLemma.wordFixCreate.reason)).toHaveFocus();
      expect(within(box).getByLabelText(trLemma.wordFixCreate.reason)).toHaveAttribute(
        'aria-invalid',
        'true',
      );
    });

    it('focuses the error of a refused send, the heading after a success, and the anchor of the next form', async () => {
      fake.post('/api/v1/word-fixes', problem(409, 'cakisma'));
      const { user } = setupGloss();
      const box = await open(user);
      fireEvent.change(within(box).getByLabelText(trLemma.wordFixCreate.anchor), {
        target: { value: 'q:1:1:3' },
      });
      fireEvent.change(within(box).getByLabelText(trLemma.wordFixCreate.value), {
        target: { value: '12' },
      });
      fireEvent.change(within(box).getByLabelText(trLemma.wordFixCreate.reason), {
        target: { value: 'QAC değeri hatalı' },
      });
      await user.click(within(box).getByRole('button', { name: trLemma.wordFixCreate.submit }));
      const alert = await within(box).findByRole('alert');
      expect(alert.parentElement).toHaveFocus();

      fake.post('/api/v1/word-fixes', ok({ id: 'fix-1', review_id: 301, durum: 'aday' }, 201));
      await user.click(within(box).getByRole('button', { name: trLemma.wordFixCreate.submit }));
      await within(box).findByTestId('word-fix-created');
      await waitFor(() =>
        expect(
          within(screen.getByTestId('word-fix-create')).getByRole('heading', {
            level: 3,
            name: trLemma.wordFixCreate.heading,
          }),
        ).toHaveFocus(),
      );
      await user.click(
        within(screen.getByTestId('word-fix-create')).getByRole('button', {
          name: trLemma.wordFixCreate.another,
        }),
      );
      expect(
        within(screen.getByTestId('word-fix-create')).getByLabelText(trLemma.wordFixCreate.anchor),
      ).toHaveFocus();
    });

    it('has no axe violation with the form open and its problems shown', async () => {
      const { container, user } = setupGloss();
      const box = await open(user);
      await user.click(within(box).getByRole('button', { name: trLemma.wordFixCreate.submit }));
      await within(box).findByTestId('word-fix-summary');
      expect(await violations(container)).toEqual([]);
    });
  });

  describe('the KWIC lines', () => {
    it('draws two lines of the same unit anchor, each with a key of its own', async () => {
      const same = 'meal:deneme:1:1';
      const kwic = [
        { capa: same, sol: 'Birinci sol ', kelime: 'kelime', sag: ' sağ bir' },
        { capa: same, sol: 'İkinci sol ', kelime: 'kelime', sag: ' sağ iki' },
        TR_KWIC[1]!,
      ];
      const spy = vi.spyOn(console, 'error').mockImplementation(() => undefined);
      try {
        setupKok({ detail: autoDetail({ kwic }) });
        const items = await screen.findAllByTestId('tr-kwic-item');
        expect(items).toHaveLength(3);
        expect(items[0]).toHaveTextContent('Birinci sol kelime sağ bir');
        expect(items[1]).toHaveTextContent('İkinci sol kelime sağ iki');
        const keyWarnings = spy.mock.calls.filter((call) => String(call[0]).includes('same key'));
        expect(keyWarnings).toEqual([]);
      } finally {
        spy.mockRestore();
      }
    });
  });
});
