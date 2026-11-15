import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import axe from 'axe-core';
import { describe, expect, it } from 'vitest';
import type { components } from '@/api/schema';
import { tr } from '@/i18n/tr';
import { trLemma } from '@/i18n/tr-lemma';
import { trLugat } from '@/i18n/tr-lugat';
import { MAX_TANIM_LENGTH } from '@/review/limits';
import { LemmaQueue } from '@/screens/lemma/lemma-queue';
import { ok, problem, useFakeApi } from './fake-api';
import { page, session, signedIn } from './fixtures';
import {
  glossItem,
  lemmaHandlers,
  lugatDetail,
  lugatItem,
  lugatSourceDetail,
  lugatSourceText,
  lugatWord,
} from './fixtures-lemma';
import { renderApp, renderInRouter } from './render-app';

type Item = components['schemas']['ReviewItemDto'];
type Detail = components['schemas']['ReviewDetailDto'];

// Synthetic lügat maddeleri (K-52 madde 9 and 10): made-up headwords and definitions, never Risale or dictionary text.

describe('Lügat tab of LemmaQueue', () => {
  const fake = useFakeApi();
  const listCalls = () => fake.callsTo('get', '/api/v1/reviews');
  const decisionCalls = () => fake.callsTo('post', '/api/v1/reviews/{id}/decision');

  function setup(opts: { items?: Item[]; detail?: Detail; route?: string } = {}) {
    const items = opts.items ?? [lugatItem(301), lugatItem(302)];
    fake.get('/api/v1/reviews', (call) =>
      ok(page(call.search.get('hedef_tablo') === 'lugat_madde' ? items : [glossItem(1)])),
    );
    lemmaHandlers(fake);
    if (opts.detail) fake.get('/api/v1/reviews/{id}', ok(opts.detail));
    fake.get('/api/v1/auth/me', ok(session()));
    fake.post('/api/v1/reviews/{id}/decision', (call) =>
      ok({
        id: Number(call.params.id),
        durum: 'onaylandi',
        eylem: 'duzenle_onayla',
        ikinci_onay_bekliyor: false,
        hedef_durumu: 'onayli',
        xmin: 900,
      }),
    );
    return renderInRouter(fake, <LemmaQueue />, opts.route ?? '/');
  }

  const openLugat = async (user: ReturnType<typeof setup>['user']) => {
    await user.click(await screen.findByRole('tab', { name: trLemma.tabs.lugat }));
  };
  const openLink = (id: number) =>
    screen.findByRole('link', { name: new RegExp(`^risale-kelime-frekans:${lugatWord(id)}`) });
  const card = () => screen.findByTestId('lugat-card');
  const field = () => screen.getByLabelText(trLugat.edit.label);
  const approve = async (user: ReturnType<typeof setup>['user']) => {
    await user.click(await screen.findByRole('radio', { name: tr.review.approve }));
  };
  const reason = (value = 'Uygun') =>
    fireEvent.change(screen.getByLabelText(tr.review.reason), { target: { value } });
  const submit = (user: ReturnType<typeof setup>['user']) =>
    user.click(screen.getByRole('button', { name: tr.review.submit }));

  describe('list', () => {
    it('is the fifth tab and lists lugat_madde + tanim_tr in descending frequency order, without a cursor and an order switch', async () => {
      const { user, router } = setup({ route: '/?kayit=301' });
      await screen.findByRole('link', { name: /^1001/ });
      await openLugat(user);
      await screen.findByRole('link', {
        name: new RegExp(`^risale-kelime-frekans:${lugatWord(301)}`),
      });
      expect(screen.getAllByRole('tab').map((tab) => tab.textContent)).toEqual([
        trLemma.tabs.anlam,
        trLemma.tabs.durum,
        trLemma.tabs.duzeltme,
        trLemma.tabs.kok,
        trLemma.tabs.lugat,
      ]);
      const last = listCalls().at(-1)!;
      expect(last.search.get('hedef_tablo')).toBe('lugat_madde');
      expect(last.search.get('alan')).toBe('tanim_tr');
      expect(last.search.get('durum')).toBe('acik');
      expect(last.search.get('sira')).toBe('siklik');
      expect(last.search.has('cursor')).toBe(false);
      expect(router.state.location.search).toBe('');
      expect(
        screen.queryByRole('radiogroup', { name: trLemma.order.label }),
      ).not.toBeInTheDocument();
      expect(screen.getByRole('tab', { name: trLemma.tabs.lugat })).toHaveAttribute(
        'aria-selected',
        'true',
      );
    });

    it('shows the frequency under each madde, and a note when there is none', async () => {
      const { user } = setup({
        items: [lugatItem(301), lugatItem(302, { onerilen: { anlam_basvuru: [] } })],
      });
      await openLugat(user);
      const frequencies = await screen.findAllByTestId('lugat-item-frequency');
      expect(frequencies.map((node) => node.textContent)).toEqual([
        trLugat.list.line('699'),
        trLugat.list.noFrequency,
      ]);
    });
  });

  describe('card', () => {
    it('shows the headword as stored, the madde, and the reference meanings labelled "Başvuru (onaysız)"', async () => {
      const { user } = setup();
      await openLugat(user);
      await user.click(
        await screen.findByRole('link', {
          name: new RegExp(`^risale-kelime-frekans:${lugatWord(301)}`),
        }),
      );
      const root = await card();
      expect(within(root).getByTestId('lugat-headword')).toHaveTextContent(lugatWord(301));
      const reference = within(root).getByTestId('lugat-reference');
      expect(
        within(reference).getByRole('heading', { name: trLugat.reference.heading }),
      ).toBeInTheDocument();
      expect(trLugat.reference.heading).toBe('Başvuru (onaysız)');
      expect(within(reference).getByText(trLugat.reference.note)).toBeInTheDocument();
      const meanings = within(reference).getByTestId('lugat-reference-meanings');
      expect(within(meanings).getAllByRole('listitem')).toHaveLength(2);
      expect(within(meanings).getByText('Deneme başvuru anlamı')).toBeInTheDocument();
      expect(within(reference).getByText(trLugat.reference.booksCount(3))).toBeInTheDocument();
      // The madde has no definition yet.
      expect(within(root).getByText(trLugat.snapshot.noDefinition)).toBeInTheDocument();
    });

    it('never offers the reference meaning as the definition: the field is empty and only appears on approval', async () => {
      const { user } = setup({ route: '/?kayit=301' });
      await card();
      expect(screen.queryByLabelText(trLugat.edit.label)).not.toBeInTheDocument();
      await user.click(await screen.findByRole('radio', { name: tr.review.reject }));
      expect(screen.queryByLabelText(trLugat.edit.label)).not.toBeInTheDocument();
      await approve(user);
      expect(field()).toHaveValue('');
      expect(field()).toHaveAttribute('lang', 'tr');
      expect(field()).toBeRequired();
      expect(
        within(screen.getByTestId('tanim-edit')).getByText(
          new RegExp(trLugat.edit.count(0, MAX_TANIM_LENGTH)),
        ),
      ).toBeInTheDocument();
    });

    it('carries no K-25 AI badge or model row: the draft is not an AI draft (yz_modeli is empty)', async () => {
      setup({ route: '/?kayit=301' });
      const root = await card();
      expect(within(root).queryByText(tr.badge.unverified)).not.toBeInTheDocument();
      expect(within(root).getByText(trLugat.origin.noAi)).toBeInTheDocument();
      expect(within(root).getByTestId('lugat-origin')).not.toHaveTextContent('Yapay zekâ modeli');
    });

    it('reads an unreadable proposal as raw text instead of failing', async () => {
      setup({ route: '/?kayit=301', detail: lugatDetail(301, { onerilen: { baska: 1 } }) });
      const reference = await screen.findByTestId('lugat-reference');
      expect(within(reference).getByText(trLugat.reference.unreadable)).toBeInTheDocument();
    });

    it('shows an existing definition and the source of the madde from the snapshot', async () => {
      setup({
        route: '/?kayit=301',
        detail: lugatDetail(301, {
          hedef: {
            tablo: 'lugat_madde',
            source: 'risale-kelime-frekans',
            basliksoz: lugatWord(301),
            tanim_tr: 'Deneme tanım metni',
            origin: 'editor',
            version: '2',
            status: 'onayli',
          },
        }),
      });
      const snapshot = await screen.findByTestId('lugat-snapshot');
      expect(within(snapshot).getByText('Deneme tanım metni')).toBeInTheDocument();
      expect(within(snapshot).getByText(trLugat.snapshot.originNames.editor)).toBeInTheDocument();
    });
  });

  describe('decision (Düzenle ve onayla)', () => {
    it('sends the written definition as duzenlenen.tanim_tr exactly as typed', async () => {
      const { user } = setup({ route: '/?kayit=301' });
      await approve(user);
      // Decomposed and padded on purpose: the server normalises (NFC), the panel never rewrites the text.
      const typed = '  café deneme tanımı ';
      fireEvent.change(field(), { target: { value: typed } });
      reason('Tanım yazıldı');
      await submit(user);
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(decisionCalls()[0]!.json).toEqual({
        karar: 'onaylandi',
        duzenlenen: { tanim_tr: typed },
        gerekce: 'Tanım yazıldı',
      });
      expect(decisionCalls()[0]!.headers.get('If-Match')).toBe('"901"');
    });

    it('refuses an empty definition next to the field and sends nothing', async () => {
      const { user } = setup({ route: '/?kayit=301' });
      await approve(user);
      reason();
      await submit(user);
      expect(decisionCalls()).toHaveLength(0);
      expect(field()).toHaveAttribute('aria-invalid', 'true');
      expect(screen.getByTestId('tanim-edit')).toHaveTextContent(trLugat.edit.empty);
      fireEvent.change(field(), { target: { value: ' \t\n ' } });
      await submit(user);
      expect(decisionCalls()).toHaveLength(0);
    });

    it('refuses a definition over 2000 characters and accepts exactly 2000', async () => {
      const { user } = setup({ route: '/?kayit=301' });
      await approve(user);
      reason();
      fireEvent.change(field(), { target: { value: 'a'.repeat(MAX_TANIM_LENGTH + 1) } });
      await submit(user);
      expect(decisionCalls()).toHaveLength(0);
      expect(screen.getByTestId('tanim-edit')).toHaveTextContent(
        trLugat.edit.tooLong(MAX_TANIM_LENGTH + 1, MAX_TANIM_LENGTH),
      );
      fireEvent.change(field(), { target: { value: 'a'.repeat(MAX_TANIM_LENGTH) } });
      await submit(user);
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
    });

    it('warns about NUL in the definition and cleans it only on request', async () => {
      const { user } = setup({ route: '/?kayit=301' });
      await approve(user);
      reason();
      fireEvent.change(field(), { target: { value: 'ab\u0000cd' } });
      await submit(user);
      expect(decisionCalls()).toHaveLength(0);
      expect(screen.getByTestId('unwritable-warning')).toBeInTheDocument();
      await user.click(screen.getByRole('button', { name: tr.review.unwritableAction }));
      expect(field()).toHaveValue('abcd');
    });

    it('does not send a definition with a rejection even after the field was filled', async () => {
      const { user } = setup({ route: '/?kayit=301' });
      await approve(user);
      fireEvent.change(field(), { target: { value: 'Deneme tanım' } });
      await user.click(screen.getByRole('radio', { name: tr.review.reject }));
      reason('Uygun değil');
      await submit(user);
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(decisionCalls()[0]!.json).toEqual({
        karar: 'reddedildi',
        duzenlenen: null,
        gerekce: 'Uygun değil',
      });
    });

    it('moves on to the next madde after the decision', async () => {
      const { user, router } = setup();
      await openLugat(user);
      await user.click(await openLink(301));
      await approve(user);
      fireEvent.change(field(), { target: { value: 'Deneme tanım' } });
      reason();
      await submit(user);
      await waitFor(() => expect(router.state.location.search).toBe('?kayit=302'));
    });

    it('shows the server answers next to the field: 400 on the field, 409 for a madde that is no longer a candidate', async () => {
      const { user } = setup({ route: '/?kayit=301' });
      await approve(user);
      fireEvent.change(field(), { target: { value: 'Deneme tanım' } });
      reason();
      fake.post(
        '/api/v1/reviews/{id}/decision',
        problem(400, 'dogrulama', { errors: { 'duzenlenen.tanim_tr': ['geçersiz'] } }),
      );
      await submit(user);
      await waitFor(() =>
        expect(screen.getByTestId('tanim-edit')).toHaveTextContent(trLugat.edit.serverInvalid),
      );
      expect(field()).toHaveAttribute('aria-invalid', 'true');
      fake.post('/api/v1/reviews/{id}/decision', problem(409, 'durum-gecisi-gecersiz'));
      await submit(user);
      await waitFor(() =>
        expect(screen.getByTestId('tanim-edit')).toHaveTextContent(trLugat.edit.notCandidate),
      );
    });

    it('explains a 422 for an approval without a definition in Turkish instead of the raw server message', async () => {
      const { user } = setup({ route: '/?kayit=301' });
      await approve(user);
      fireEvent.change(field(), { target: { value: 'Deneme tanım' } });
      reason();
      fake.post(
        '/api/v1/reviews/{id}/decision',
        problem(422, 'inceleme-desteklenmiyor', {
          detail: 'Lugat maddesi bos tanimla onaylanamaz; duzenlenen.tanim_tr ile tanimi yazin.',
        }),
      );
      await submit(user);
      await screen.findByText(tr.problem.lugatDefinitionRequired);
      expect(screen.queryByText(/Lugat maddesi bos tanimla/)).not.toBeInTheDocument();
    });
  });

  describe('source definition (K-52 madde 10 and 14)', () => {
    const editButton = () => screen.getByRole('button', { name: trLugat.edit.editAndApprove });

    it('shows the source name, the meaning number, the source definition and the origin badge', async () => {
      setup({
        route: '/?kayit=301',
        detail: lugatSourceDetail(301, { source: 'lugat-sozluk-rganeyev', anlamNo: 2 }),
      });
      const snapshot = await screen.findByTestId('lugat-snapshot');
      expect(within(snapshot).getByTestId('lugat-source')).toHaveTextContent(
        trLugat.sources['lugat-sozluk-rganeyev']!,
      );
      expect(within(snapshot).getByTestId('lugat-meaning')).toHaveTextContent(trLugat.meaning(2));
      expect(within(snapshot).getByText(lugatSourceText(301))).toBeInTheDocument();
      expect(within(snapshot).getByText(trLugat.snapshot.sourceDefinition)).toBeInTheDocument();
      expect(within(snapshot).getByText(trLugat.snapshot.originNames.kaynak)).toBeInTheDocument();
    });

    it('approves the source definition unchanged: no field, no edit in the body', async () => {
      const { user } = setup({ route: '/?kayit=301', detail: lugatSourceDetail(301) });
      await card();
      await approve(user);
      expect(screen.queryByLabelText(trLugat.edit.label)).not.toBeInTheDocument();
      expect(screen.getByText(trLugat.edit.unchangedNote)).toBeInTheDocument();
      expect(editButton()).toHaveAttribute('aria-pressed', 'false');
      reason('Kaynakla uyumlu');
      await submit(user);
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(decisionCalls()[0]!.json).toEqual({
        karar: 'onaylandi',
        duzenlenen: null,
        gerekce: 'Kaynakla uyumlu',
      });
    });

    it('"Düzenle ve onayla" opens the field with the source definition and sends the changed text', async () => {
      const { user } = setup({ route: '/?kayit=301', detail: lugatSourceDetail(301) });
      await card();
      await approve(user);
      await user.click(editButton());
      expect(field()).toHaveValue(lugatSourceText(301));
      expect(screen.getByRole('button', { name: trLugat.edit.cancelEdit })).toHaveAttribute(
        'aria-pressed',
        'true',
      );
      fireEvent.change(field(), { target: { value: 'Düzeltilmiş deneme tanımı' } });
      reason('Düzeltildi');
      await submit(user);
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(decisionCalls()[0]!.json).toEqual({
        karar: 'onaylandi',
        duzenlenen: { tanim_tr: 'Düzeltilmiş deneme tanımı' },
        gerekce: 'Düzeltildi',
      });
    });

    it('sends no edit when the opened field still equals the source definition, and cancelling closes it', async () => {
      const { user } = setup({ route: '/?kayit=301', detail: lugatSourceDetail(301) });
      await card();
      await approve(user);
      await user.click(editButton());
      fireEvent.change(field(), { target: { value: 'Geçici' } });
      await user.click(screen.getByRole('button', { name: trLugat.edit.cancelEdit }));
      expect(screen.queryByLabelText(trLugat.edit.label)).not.toBeInTheDocument();
      await user.click(editButton());
      expect(field()).toHaveValue(lugatSourceText(301));
      reason();
      await submit(user);
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(decisionCalls()[0]!.json).toEqual({
        karar: 'onaylandi',
        duzenlenen: null,
        gerekce: 'Uygun',
      });
    });

    it('refuses an emptied definition while editing a source definition', async () => {
      const { user } = setup({ route: '/?kayit=301', detail: lugatSourceDetail(301) });
      await card();
      await approve(user);
      await user.click(editButton());
      fireEvent.change(field(), { target: { value: '  ' } });
      reason();
      await submit(user);
      expect(decisionCalls()).toHaveLength(0);
      expect(screen.getByTestId('tanim-edit')).toHaveTextContent(trLugat.edit.empty);
    });

    it('offers no unchanged approval for a madde without a source definition: only the field', async () => {
      const { user } = setup({
        route: '/?kayit=301',
        detail: lugatSourceDetail(301, { tanim: null }),
      });
      await card();
      await approve(user);
      expect(field()).toHaveValue('');
      expect(
        screen.queryByRole('button', { name: trLugat.edit.editAndApprove }),
      ).not.toBeInTheDocument();
      expect(screen.queryByText(trLugat.edit.unchangedNote)).not.toBeInTheDocument();
    });

    it('does not send an edit with a rejection', async () => {
      const { user } = setup({ route: '/?kayit=301', detail: lugatSourceDetail(301) });
      await card();
      await user.click(await screen.findByRole('radio', { name: tr.review.reject }));
      expect(
        screen.queryByRole('button', { name: trLugat.edit.editAndApprove }),
      ).not.toBeInTheDocument();
      reason('Uygun değil');
      await submit(user);
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(decisionCalls()[0]!.json).toEqual({
        karar: 'reddedildi',
        duzenlenen: null,
        gerekce: 'Uygun değil',
      });
    });

    it('shows the source name and the meaning number under each madde of the list (legacy key: meaning 1)', async () => {
      const { user } = setup({
        items: [lugatItem(301, { hedef_anahtar: `lugat-rnk:2:${lugatWord(301)}` }), lugatItem(302)],
      });
      await openLugat(user);
      await screen.findAllByTestId('lugat-item-source');
      expect(screen.getAllByTestId('lugat-item-source').map((node) => node.textContent)).toEqual([
        trLugat.list.meaningSource(trLugat.sources['lugat-rnk']!, 2),
        trLugat.list.meaningSource(trLugat.sources['risale-kelime-frekans']!, 1),
      ]);
    });

    it('has no axe violations with the source definition card and the edit field open', async () => {
      fake.get('/api/v1/reviews/{id}', ok(lugatSourceDetail(301)));
      signedIn(fake);
      fake.get(
        '/api/v1/reviews',
        ok(page([lugatItem(301, { hedef_anahtar: `lugat-rnk:1:${lugatWord(301)}` })])),
      );
      const { container, user } = renderApp(fake, '/kuyruk/lemma?kayit=301');
      await user.click(await screen.findByRole('tab', { name: trLemma.tabs.lugat }));
      await user.click(
        await screen.findByRole('link', { name: new RegExp(`^lugat-rnk:1:${lugatWord(301)}`) }),
      );
      await card();
      await user.click(await screen.findByRole('radio', { name: tr.review.approve }));
      await user.click(editButton());
      await screen.findByTestId('tanim-edit');
      const result = await axe.run(container, {
        rules: { 'color-contrast': { enabled: false }, 'target-size': { enabled: false } },
      });
      expect(
        result.violations.map(
          (violation) =>
            `${violation.id}: ${violation.nodes.map((node) => node.target.join(' ')).join(' | ')}`,
        ),
      ).toEqual([]);
    });
  });

  describe('sidebar and accessibility', () => {
    it('counts the lugat_madde queue in the open records of the Kelime anlamları entry', async () => {
      lemmaHandlers(fake);
      signedIn(fake);
      fake.get(
        '/api/v1/reviews/stats',
        ok({
          kuyruklar: [
            { hedef_tablo: 'lemma_gloss', alan: 'anlam_kisa', acik: 2 },
            { hedef_tablo: 'lugat_madde', alan: 'tanim_tr', acik: 5 },
          ],
          toplam_acik: 7,
          baglanti_siniflari: [],
          toplam_uzmanda: 0,
        }),
      );
      fake.get('/api/v1/reviews', ok(page([glossItem(1)])));
      renderApp(fake, '/kuyruk/lemma');
      const nav = await screen.findByRole('navigation', { name: tr.nav.label });
      await within(nav).findByText('7');
    });

    it('has no axe violations (the tab, the card and the decision form with the definition field)', async () => {
      fake.get('/api/v1/reviews/{id}', ok(lugatDetail(301)));
      signedIn(fake);
      fake.get('/api/v1/reviews', ok(page([lugatItem(301)])));
      const { container, user } = renderApp(fake, '/kuyruk/lemma?kayit=301');
      await user.click(await screen.findByRole('tab', { name: trLemma.tabs.lugat }));
      await user.click(await openLink(301));
      await card();
      await user.click(await screen.findByRole('radio', { name: tr.review.approve }));
      await screen.findByTestId('tanim-edit');
      const result = await axe.run(container, {
        rules: { 'color-contrast': { enabled: false }, 'target-size': { enabled: false } },
      });
      expect(
        result.violations.map(
          (violation) =>
            `${violation.id}: ${violation.nodes.map((node) => node.target.join(' ')).join(' | ')}`,
        ),
      ).toEqual([]);
    });
  });
});

describe('trLugat', () => {
  it('has no empty text', () => {
    const walk = (value: unknown, path: string): string[] => {
      if (typeof value === 'string') return value.trim() === '' ? [path] : [];
      if (typeof value === 'function') return [];
      if (typeof value === 'object' && value !== null) {
        return Object.entries(value).flatMap(([key, entry]) => walk(entry, `${path}.${key}`));
      }
      return [];
    };
    expect(walk(trLugat, 'trLugat')).toEqual([]);
  });
});
