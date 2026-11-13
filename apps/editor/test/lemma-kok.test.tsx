import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import axe from 'axe-core';
import { describe, expect, it } from 'vitest';
import type { components } from '@/api/schema';
import { tr } from '@/i18n/tr';
import { trLemma } from '@/i18n/tr-lemma';
import { LemmaQueue } from '@/screens/lemma/lemma-queue';
import { ok, problem, useFakeApi } from './fake-api';
import { page, session } from './fixtures';
import {
  LEMMA_ARABIC,
  ROOT_ARABIC,
  TR_KWIC,
  kokDetail,
  kokItem,
  lemmaInfo,
  objectionDetail,
  objectionItem,
  trTarget,
} from './fixtures-lemma';
import { renderInRouter } from './render-app';

type Item = components['schemas']['ReviewItemDto'];
type Detail = components['schemas']['ReviewDetailDto'];

describe('Turkish lemma root mapping queue (A18.2)', () => {
  const fake = useFakeApi();
  const listCalls = () => fake.callsTo('get', '/api/v1/reviews');
  const decisionCalls = () => fake.callsTo('post', '/api/v1/reviews/{id}/decision');
  const objectionCalls = () => fake.callsTo('post', '/api/v1/lemmas/{id}/itiraz');
  const etymologyCalls = () => fake.callsTo('post', '/api/v1/lemmas/{id}/etimolojik-isaret');

  function setup(opts: { items?: Item[]; details?: Record<number, Detail>; route?: string } = {}) {
    const items = opts.items ?? [kokItem(1), kokItem(2)];
    const details: Record<number, Detail> = {
      1: kokDetail(1),
      2: kokDetail(2),
      ...opts.details,
    };
    // Mirrors the server: `onay_yolu` filters by the approval path of the lemma (a candidate has none).
    fake.get('/api/v1/reviews', (call) => {
      const wanted = call.search.get('onay_yolu');
      const rows = items.filter(
        (item) =>
          wanted === null ||
          (wanted === 'aday' ? item.onay_yolu == null : item.onay_yolu === wanted),
      );
      return ok(page(call.search.get('alan') === 'kok_eslemesi' ? rows : []));
    });
    fake.get('/api/v1/reviews/{id}', (call) => ok(details[Number(call.params.id)]!));
    fake.get('/api/v1/lemmas/{id}', ok(lemmaInfo()));
    fake.get('/api/v1/auth/me', ok(session()));
    fake.post('/api/v1/reviews/{id}/decision', (call) =>
      ok({
        id: Number(call.params.id),
        durum: 'onaylandi',
        eylem: 'onayla',
        ikinci_onay_bekliyor: false,
        hedef_durumu: 'onayli',
        xmin: 900,
      }),
    );
    return renderInRouter(fake, <LemmaQueue />, opts.route ?? '/');
  }

  const card = () => screen.findByTestId('lemma-card');
  type User = ReturnType<typeof setup>['user'];

  describe('the tab', () => {
    it('lists lemma + kok_eslemesi in creation order: no sira, no cursor, 50 per page', async () => {
      const { user } = setup();
      await user.click(await screen.findByRole('tab', { name: trLemma.tabs.kok }));
      await screen.findByRole('link', { name: /^3001/ });
      const last = listCalls().at(-1)!;
      expect(last.search.get('hedef_tablo')).toBe('lemma');
      expect(last.search.get('alan')).toBe('kok_eslemesi');
      expect(last.search.get('durum')).toBe('acik');
      expect(last.search.get('limit')).toBe('50');
      expect(last.search.has('sira')).toBe(false);
      expect(last.search.has('cursor')).toBe(false);
      expect(
        screen.queryByRole('radiogroup', { name: trLemma.order.label }),
      ).not.toBeInTheDocument();
      expect(screen.getByText(trLemma.tabHints.kok)).toBeInTheDocument();
    });
  });

  describe('the card of a candidate', () => {
    it('shows the lemma, the proposed root letters, the Arabic lemma, frequency and the status', async () => {
      setup({ route: '/?kayit=1' });
      const root = await card();
      expect(
        within(root).getByRole('heading', { level: 2, name: trLemma.heading.kok }),
      ).toBeInTheDocument();
      const summary = within(root).getByTestId('tr-lemma-summary');
      expect(within(summary).getByText('deneme-kelime-1')).toHaveAttribute('lang', 'tr');
      expect(within(summary).getByText(trLemma.kok.proposedRoot)).toBeInTheDocument();
      const letters = within(summary).getByText(ROOT_ARABIC);
      expect(letters).toHaveAttribute('lang', 'ar');
      expect(letters).toHaveAttribute('dir', 'rtl');
      const arabic = within(summary).getByText(LEMMA_ARABIC);
      expect(arabic).toHaveAttribute('lang', 'ar');
      expect(arabic).toHaveAttribute('dir', 'rtl');
      expect(within(summary).getByText('12')).toBeInTheDocument();
      expect(within(summary).getByText(trLemma.kok.freq)).toBeInTheDocument();
      expect(within(summary).getByText(trLemma.kok.approvalPath).nextSibling).toHaveTextContent(
        trLemma.kok.none,
      );
      // A candidate carries no approval badge, only the candidate badge; the proposal is read from onerilen.
      expect(screen.queryByTestId('approval-badge')).not.toBeInTheDocument();
      expect(screen.getByTestId('candidate-badge')).toHaveTextContent(trLemma.approval.aday);
      expect(within(root).getByTestId('tr-lemma-proposal')).toHaveTextContent('1001');
      // A candidate is no AI draft: no unverified badge.
      expect(screen.queryByText(tr.badge.unverified)).not.toBeInTheDocument();
    });

    it('draws the KWIC lines with the word highlighted and marks a line with null parts as stale', async () => {
      setup({ route: '/?kayit=1' });
      await card();
      const lines = screen.getAllByTestId('tr-kwic-item');
      expect(lines).toHaveLength(3);
      const first = lines[0]!;
      expect(first.querySelector('mark')).toHaveTextContent('kelime');
      expect(first.querySelector('p[lang="tr"]')).toHaveTextContent('Deneme sol kelime sağ bir');
      expect(within(first).getByText('meal:deneme:1:1@0-10')).toHaveAttribute('dir', 'ltr');
      const stale = lines[2]!;
      expect(within(stale).getByTestId('tr-kwic-stale')).toHaveTextContent(trLemma.kok.kwic.stale);
      expect(stale.querySelector('mark')).toBeNull();
      expect(screen.getAllByTestId('tr-kwic-stale')).toHaveLength(1);
    });

    it('says "Veri yok" when the snapshot has no KWIC and no evidence, and invents nothing', async () => {
      setup({
        route: '/?kayit=3',
        details: { 3: kokDetail(3, { hedef: trTarget(3, { kwic: [], kanit_ozeti: null }) }) },
      });
      await card();
      expect(
        within(screen.getByTestId('tr-lemma-kwic')).getByText(trLemma.kok.kwic.none),
      ).toBeInTheDocument();
      expect(screen.queryByTestId('tr-kwic-item')).not.toBeInTheDocument();
      expect(
        within(screen.getByTestId('tr-lemma-evidence')).getByText(trLemma.kok.evidence.none),
      ).toBeInTheDocument();
    });

    it('shows the evidence summary: source count, QAC match type, decision, reason, policy version', async () => {
      setup({ route: '/?kayit=1' });
      await card();
      const evidence = screen.getByTestId('tr-lemma-evidence');
      const text = trLemma.kok.evidence;
      expect(within(evidence).getByText(text.sources).nextSibling).toHaveTextContent('3');
      expect(within(evidence).getByText(text.qac).nextSibling).toHaveTextContent('harfler');
      expect(within(evidence).getByText(text.decision).nextSibling).toHaveTextContent(
        'otomatik_onay',
      );
      expect(within(evidence).getByText(text.reason).nextSibling).toHaveTextContent(
        'yapisal_kanit',
      );
      expect(within(evidence).getByText(text.policy).nextSibling).toHaveTextContent(
        'deneme-politika-1',
      );
    });

    it('says the mapping has no snapshot instead of drawing an empty card', async () => {
      setup({ route: '/?kayit=3', details: { 3: kokDetail(3, { hedef: null }) } });
      await card();
      expect(screen.getByText(trLemma.kok.missing)).toBeInTheDocument();
    });

    it('does not request the Arabic lemma card of GET /lemmas/{id} for a Turkish lemma', async () => {
      setup({ route: '/?kayit=1' });
      await card();
      expect(fake.callsTo('get', '/api/v1/lemmas/{id}')).toHaveLength(0);
    });

    it('points a candidate to the edit-and-approve option for the etymological mark, and has no objection', async () => {
      setup({ route: '/?kayit=1' });
      await card();
      expect(screen.getByText(trLemma.kok.etym.candidateNote)).toBeInTheDocument();
      expect(
        screen.queryByRole('button', { name: trLemma.kok.objection.open }),
      ).not.toBeInTheDocument();
      expect(screen.getByText(trLemma.decisionNote.kok)).toBeInTheDocument();
    });
  });

  describe('the approval path', () => {
    const autoDetail = () =>
      kokDetail(4, { hedef: trTarget(4, { status: 'onayli', onay_yolu: 'otomatik' }) });
    const editorDetail = () =>
      kokDetail(5, { hedef: trTarget(5, { status: 'onayli', onay_yolu: 'editor' }) });

    it('marks an automatic approval "Sözlük kanıtıyla otomatik", not "Editör onaylı", and reads it out', async () => {
      setup({ route: '/?kayit=4', details: { 4: autoDetail() } });
      await card();
      const badge = screen.getByTestId('approval-badge');
      expect(badge).toHaveAttribute('data-approval-path', 'otomatik');
      expect(badge).toHaveTextContent(trLemma.approval.otomatik);
      expect(screen.queryByText(trLemma.approval.editor)).not.toBeInTheDocument();
      // The explanation is hidden text tied to the badge; the meaning is not in the colour.
      expect(badge).toHaveAccessibleDescription(trLemma.approval.otomatikHint);
      expect(badge.querySelector('svg')).toHaveAttribute('aria-hidden', 'true');
      // It is not the K-25 unverified badge.
      expect(screen.queryByText(tr.badge.unverified)).not.toBeInTheDocument();
      const summary = screen.getByTestId('tr-lemma-summary');
      expect(within(summary).getByText(trLemma.kok.approvalPath).nextSibling).toHaveTextContent(
        trLemma.approval.otomatik,
      );
    });

    it('marks an editor approval "Editör onaylı"', async () => {
      setup({ route: '/?kayit=5', details: { 5: editorDetail() } });
      await card();
      const badge = screen.getByTestId('approval-badge');
      expect(badge).toHaveAttribute('data-approval-path', 'editor');
      expect(badge).toHaveTextContent(trLemma.approval.editor);
      expect(badge).toHaveAccessibleDescription(trLemma.approval.editorHint);
      expect(screen.queryByText(trLemma.approval.otomatik)).not.toBeInTheDocument();
    });

    it('draws an unknown path as no badge (it is not guessed)', async () => {
      setup({
        route: '/?kayit=6',
        details: {
          6: kokDetail(6, { hedef: trTarget(6, { status: 'onayli', onay_yolu: 'baska' }) }),
        },
      });
      await card();
      expect(screen.queryByTestId('approval-badge')).not.toBeInTheDocument();
    });
  });

  describe('edit and approve', () => {
    const approve = async (user: User) => {
      await user.click(await screen.findByRole('radio', { name: tr.review.approve }));
    };
    const reason = (value = 'Uygun') =>
      fireEvent.change(screen.getByLabelText(tr.review.reason), { target: { value } });
    const submit = (user: User) =>
      user.click(screen.getByRole('button', { name: tr.review.submit }));
    const rootField = () => screen.getByLabelText(trLemma.kok.edit.rootId);
    const arField = () => screen.getByLabelText(trLemma.kok.edit.arLemmaId);
    const etym = () => screen.getByRole('checkbox', { name: trLemma.kok.edit.etymological });

    it('shows the fields only on approval, filled with the proposal', async () => {
      const { user } = setup({ route: '/?kayit=1' });
      await card();
      expect(screen.queryByTestId('mapping-edit')).not.toBeInTheDocument();
      await user.click(await screen.findByRole('radio', { name: tr.review.reject }));
      expect(screen.queryByTestId('mapping-edit')).not.toBeInTheDocument();
      await approve(user);
      expect(rootField()).toHaveValue('7');
      expect(rootField()).toHaveAttribute('dir', 'ltr');
      expect(arField()).toHaveValue('1001');
      expect(etym()).not.toBeChecked();
      // It does not replace the meal-text or meaning fields.
      expect(screen.queryByLabelText(tr.review.editedText)).not.toBeInTheDocument();
      expect(screen.queryByLabelText(trLemma.edit.label)).not.toBeInTheDocument();
    });

    it('sends a plain approval (duzenlenen null) when nothing changed', async () => {
      const { user } = setup({ route: '/?kayit=1' });
      await approve(user);
      reason();
      await submit(user);
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(decisionCalls()[0]!.headers.get('If-Match')).toBe('"601"');
      expect(decisionCalls()[0]!.json).toEqual({
        karar: 'onaylandi',
        duzenlenen: null,
        gerekce: 'Uygun',
      });
    });

    it('sends root_id, ar_lemma_id and etymological_only as duzenlenen', async () => {
      const { user } = setup({ route: '/?kayit=1' });
      await approve(user);
      fireEvent.change(rootField(), { target: { value: '9' } });
      fireEvent.change(arField(), { target: { value: '1002' } });
      await user.click(etym());
      reason('Daha doğru');
      await submit(user);
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(decisionCalls()[0]!.json).toEqual({
        karar: 'onaylandi',
        duzenlenen: { root_id: 9, ar_lemma_id: 1002, etymological_only: true },
        gerekce: 'Daha doğru',
      });
    });

    it('sends ar_lemma_id null when the Arabic lemma is cleared (no Arabic counterpart)', async () => {
      const { user } = setup({ route: '/?kayit=1' });
      await approve(user);
      fireEvent.change(arField(), { target: { value: '' } });
      reason();
      await submit(user);
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(decisionCalls()[0]!.json).toEqual({
        karar: 'onaylandi',
        duzenlenen: { root_id: 7, ar_lemma_id: null, etymological_only: false },
        gerekce: 'Uygun',
      });
    });

    it('does not send an edit with a rejection even after the fields were changed', async () => {
      const { user } = setup({ route: '/?kayit=1' });
      await approve(user);
      fireEvent.change(rootField(), { target: { value: '9' } });
      await user.click(screen.getByRole('radio', { name: tr.review.reject }));
      reason();
      await submit(user);
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(decisionCalls()[0]!.json).toEqual({
        karar: 'reddedildi',
        duzenlenen: null,
        gerekce: 'Uygun',
      });
    });

    it('refuses an empty or malformed id next to its field and sends nothing', async () => {
      const { user } = setup({ route: '/?kayit=1' });
      await approve(user);
      fireEvent.change(rootField(), { target: { value: '' } });
      reason();
      await submit(user);
      expect(await screen.findByTestId('decision-summary')).toHaveTextContent(
        trLemma.kok.edit.rootRequired,
      );
      expect(rootField()).toHaveAttribute('aria-invalid', 'true');
      fireEvent.change(rootField(), { target: { value: '7' } });
      fireEvent.change(arField(), { target: { value: '12x' } });
      await submit(user);
      await waitFor(() =>
        expect(screen.getByTestId('decision-summary')).toHaveTextContent(
          trLemma.kok.edit.arInvalid,
        ),
      );
      expect(arField()).toHaveAttribute('aria-invalid', 'true');
      expect(decisionCalls()).toHaveLength(0);
    });

    it('needs the root id also when the proposal has none', async () => {
      const { user } = setup({
        route: '/?kayit=3',
        details: {
          3: kokDetail(3, {
            onerilen: null,
            hedef: trTarget(3, {
              root_id: null,
              ar_lemma_id: null,
              root_letters: null,
              ar_lemma_text: null,
            }),
          }),
        },
      });
      await approve(user);
      expect(rootField()).toHaveValue('');
      reason();
      await submit(user);
      expect(await screen.findByTestId('decision-summary')).toHaveTextContent(
        trLemma.kok.edit.rootRequired,
      );
      expect(decisionCalls()).toHaveLength(0);
    });

    it('shows a 400 dogrulama on the fields in Turkish with the server message, and keeps the input', async () => {
      const { user } = setup({ route: '/?kayit=1' });
      await approve(user);
      fireEvent.change(rootField(), { target: { value: '99' } });
      reason();
      fake.post(
        '/api/v1/reviews/{id}/decision',
        problem(400, 'dogrulama', { detail: 'root_id 99 diye bir kok yok.' }),
      );
      await submit(user);
      const summary = await screen.findByTestId('decision-summary');
      expect(summary).toHaveTextContent(trLemma.kok.edit.serverInvalid);
      expect(summary).toHaveTextContent('root_id 99 diye bir kok yok.');
      expect(rootField()).toHaveAttribute('aria-invalid', 'true');
      expect(rootField()).toHaveValue('99');
      expect(screen.getByLabelText(tr.review.reason)).toHaveValue('Uygun');
    });

    it('shows a 409 as the usual decision problem, not on the fields', async () => {
      const { user } = setup({ route: '/?kayit=1' });
      await approve(user);
      fireEvent.change(rootField(), { target: { value: '9' } });
      reason();
      fake.post('/api/v1/reviews/{id}/decision', problem(409, 'durum-gecisi-gecersiz'));
      await submit(user);
      await waitFor(() =>
        expect(
          document.querySelector('[data-problem-code="durum-gecisi-gecersiz"]'),
        ).not.toBeNull(),
      );
      expect(rootField()).not.toHaveAttribute('aria-invalid');
    });

    it('previews the typed Arabic lemma, warns when its root differs and takes the root from it', async () => {
      const { user } = setup({ route: '/?kayit=1' });
      await approve(user);
      const preview = await screen.findByTestId('ar-lemma-preview');
      expect(fake.callsTo('get', '/api/v1/lemmas/{id}').at(-1)!.params.id).toBe('1001');
      expect(await within(preview).findByText(LEMMA_ARABIC)).toHaveAttribute('lang', 'ar');
      expect(within(preview).getByText(ROOT_ARABIC)).toHaveAttribute('dir', 'rtl');
      // The synthetic lemma card has root 7, the proposal too: no warning.
      expect(within(preview).queryByText(trLemma.kok.edit.preview.useRoot)).not.toBeInTheDocument();
      fireEvent.change(rootField(), { target: { value: '9' } });
      expect(
        await within(preview).findByText(trLemma.kok.edit.preview.mismatch(7)),
      ).toBeInTheDocument();
      await user.click(
        within(preview).getByRole('button', { name: trLemma.kok.edit.preview.useRoot }),
      );
      expect(rootField()).toHaveValue('7');
    });

    it('says so when the typed Arabic lemma is not Arabic or cannot be loaded', async () => {
      const { user } = setup({ route: '/?kayit=1' });
      fake.get(
        '/api/v1/lemmas/{id}',
        ok(lemmaInfo({ lemma: { ...lemmaInfo().lemma, lang: 'tr' } })),
      );
      await approve(user);
      const preview = await screen.findByTestId('ar-lemma-preview');
      expect(
        await within(preview).findByText(trLemma.kok.edit.preview.notArabic),
      ).toBeInTheDocument();
      fake.get('/api/v1/lemmas/{id}', problem(404, 'bulunamadi'));
      fireEvent.change(arField(), { target: { value: '55' } });
      expect(
        await within(screen.getByTestId('ar-lemma-preview')).findByText(
          trLemma.kok.edit.preview.failed,
        ),
      ).toBeInTheDocument();
    });

    it('has no edit fields on an objection record; approval is plain', async () => {
      const { user } = setup({ route: '/?kayit=7', details: { 7: objectionDetail(7) } });
      await card();
      await approve(user);
      expect(screen.queryByTestId('mapping-edit')).not.toBeInTheDocument();
      expect(screen.getByText(trLemma.decisionNote.itiraz)).toBeInTheDocument();
      reason();
      await submit(user);
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(decisionCalls()[0]!.json).toEqual({
        karar: 'onaylandi',
        duzenlenen: null,
        gerekce: 'Uygun',
      });
    });
  });

  describe('objection to an automatic approval', () => {
    const autoDetail = () =>
      kokDetail(4, { hedef: trTarget(4, { status: 'onayli', onay_yolu: 'otomatik' }) });
    const open = async (user: User) => {
      await user.click(await screen.findByRole('button', { name: trLemma.kok.objection.open }));
    };
    const reasonField = () => screen.getByLabelText(trLemma.kok.objection.reason);
    const send = (user: User) =>
      user.click(screen.getByRole('button', { name: trLemma.kok.objection.submit }));

    it('offers "İtiraz et" only on an approved lemma with the automatic path', async () => {
      setup({
        route: '/?kayit=5',
        details: {
          5: kokDetail(5, { hedef: trTarget(5, { status: 'onayli', onay_yolu: 'editor' }) }),
        },
      });
      await card();
      expect(
        screen.queryByRole('button', { name: trLemma.kok.objection.open }),
      ).not.toBeInTheDocument();
    });

    it('offers no objection on an objection record itself (one is open already)', async () => {
      setup({ route: '/?kayit=7', details: { 7: objectionDetail(7) } });
      await card();
      expect(
        screen.queryByRole('button', { name: trLemma.kok.objection.open }),
      ).not.toBeInTheDocument();
      expect(screen.getByTestId('objection-note')).toHaveTextContent('Deneme itiraz gerekçesi');
      expect(screen.getByTestId('approval-badge')).toHaveAttribute(
        'data-approval-path',
        'otomatik',
      );
    });

    it('needs a reason: nothing is sent without it, and the error is tied to the field', async () => {
      const { user } = setup({ route: '/?kayit=4', details: { 4: autoDetail() } });
      await card();
      await open(user);
      await send(user);
      expect(await screen.findByText(trLemma.kok.objection.reasonRequired)).toBeInTheDocument();
      expect(reasonField()).toHaveAttribute('aria-invalid', 'true');
      expect(reasonField()).toHaveAccessibleDescription(
        new RegExp(trLemma.kok.objection.reasonRequired),
      );
      expect(objectionCalls()).toHaveLength(0);
    });

    it('opens the form with focus order: button, then reason, send and cancel', async () => {
      const { user } = setup({ route: '/?kayit=4', details: { 4: autoDetail() } });
      await card();
      await open(user);
      expect(
        screen.queryByRole('button', { name: trLemma.kok.objection.open }),
      ).not.toBeInTheDocument();
      await user.click(reasonField());
      await user.tab();
      expect(screen.getByRole('button', { name: trLemma.kok.objection.submit })).toHaveFocus();
      await user.tab();
      expect(screen.getByRole('button', { name: trLemma.kok.objection.cancel })).toHaveFocus();
      await user.click(screen.getByRole('button', { name: trLemma.kok.objection.cancel }));
      expect(screen.getByRole('button', { name: trLemma.kok.objection.open })).toBeInTheDocument();
    });

    it('posts {gerekce} to the lemma and says "İtiraz kaydı açıldı"; no second objection is offered', async () => {
      fake.post('/api/v1/lemmas/{id}/itiraz', ok({ id: 77, durum: 'acik' }, 201));
      const { user } = setup({ route: '/?kayit=4', details: { 4: autoDetail() } });
      await card();
      await open(user);
      fireEvent.change(reasonField(), { target: { value: 'Kök yanlış görünüyor' } });
      await send(user);
      await waitFor(() => expect(objectionCalls()).toHaveLength(1));
      const call = objectionCalls()[0]!;
      expect(call.params.id).toBe('3004');
      expect(call.json).toEqual({ gerekce: 'Kök yanlış görünüyor' });
      const done = await screen.findByTestId('objection-done');
      expect(done).toHaveTextContent('İtiraz kaydı açıldı');
      expect(done).toHaveTextContent(trLemma.kok.objection.doneId(77));
      expect(
        screen.queryByRole('button', { name: trLemma.kok.objection.open }),
      ).not.toBeInTheDocument();
      // The record is read again after the action.
      await waitFor(() =>
        expect(fake.callsTo('get', '/api/v1/reviews/{id}').length).toBeGreaterThan(1),
      );
    });

    it.each([
      [409, 'durum-gecisi-gecersiz'],
      [422, 'inceleme-desteklenmiyor'],
      [400, 'dogrulama'],
      [404, 'bulunamadi'],
    ] as const)('shows %i in Turkish and keeps the input', async (status, kod) => {
      fake.post('/api/v1/lemmas/{id}/itiraz', problem(status, kod));
      const { user } = setup({ route: '/?kayit=4', details: { 4: autoDetail() } });
      await card();
      await open(user);
      fireEvent.change(reasonField(), { target: { value: 'Kök yanlış görünüyor' } });
      await send(user);
      const alert = await screen.findByTestId('objection-error');
      expect(alert).toHaveTextContent(trLemma.kok.objection.errors[status]);
      expect(alert).toHaveAttribute('data-problem-code', kod);
      expect(reasonField()).toHaveValue('Kök yanlış görünüyor');
      expect(screen.queryByTestId('objection-done')).not.toBeInTheDocument();
    });

    it('shows any other problem as the generic problem message', async () => {
      fake.post('/api/v1/lemmas/{id}/itiraz', problem(500, 'sunucu-hatasi'));
      const { user } = setup({ route: '/?kayit=4', details: { 4: autoDetail() } });
      await card();
      await open(user);
      fireEvent.change(reasonField(), { target: { value: 'Neden' } });
      await send(user);
      await waitFor(() =>
        expect(document.querySelector('[data-problem-code="sunucu-hatasi"]')).not.toBeNull(),
      );
      expect(screen.queryByTestId('objection-error')).not.toBeInTheDocument();
    });
  });

  describe('the etymological mark', () => {
    const approved = (path: 'otomatik' | 'editor', over = {}) =>
      kokDetail(4, { hedef: trTarget(4, { status: 'onayli', onay_yolu: path, ...over }) });
    const checkbox = () => screen.getByRole('checkbox', { name: trLemma.kok.etym.checkbox });
    const reasonField = () => screen.getByLabelText(trLemma.kok.etym.reason);
    const save = (user: User) =>
      user.click(screen.getByRole('button', { name: trLemma.kok.etym.submit }));

    it('shows the current value and the switch on an approved mapping only', async () => {
      setup({
        route: '/?kayit=4',
        details: { 4: approved('editor', { etymological_only: true }) },
      });
      await card();
      const section = screen.getByTestId('lemma-etymology');
      expect(section).toHaveTextContent(trLemma.kok.etym.current(trLemma.kok.yes));
      expect(checkbox()).toBeChecked();
    });

    it('says a lemma without a root cannot be marked', async () => {
      setup({
        route: '/?kayit=4',
        details: { 4: approved('otomatik', { root_id: null, root_letters: null }) },
      });
      await card();
      expect(screen.getByText(trLemma.kok.etym.noRoot)).toBeInTheDocument();
      expect(
        screen.queryByRole('checkbox', { name: trLemma.kok.etym.checkbox }),
      ).not.toBeInTheDocument();
    });

    it('refuses an unchanged value and an empty reason before anything is sent', async () => {
      const { user } = setup({ route: '/?kayit=4', details: { 4: approved('otomatik') } });
      await card();
      await save(user);
      expect(await screen.findByText(trLemma.kok.etym.unchanged)).toBeInTheDocument();
      await user.click(checkbox());
      await save(user);
      expect(await screen.findByText(trLemma.kok.etym.reasonRequired)).toBeInTheDocument();
      expect(etymologyCalls()).toHaveLength(0);
    });

    it('posts the new value and the reason, and says the lemma is editor approved now', async () => {
      fake.post(
        '/api/v1/lemmas/{id}/etimolojik-isaret',
        ok({ review_id: 88, etymological_only: true, onay_yolu: 'editor', status: 'onayli' }),
      );
      const { user } = setup({ route: '/?kayit=4', details: { 4: approved('otomatik') } });
      await card();
      await user.click(checkbox());
      fireEvent.change(reasonField(), { target: { value: 'Anlam kaymış' } });
      await save(user);
      await waitFor(() => expect(etymologyCalls()).toHaveLength(1));
      const call = etymologyCalls()[0]!;
      expect(call.params.id).toBe('3004');
      expect(call.json).toEqual({ etymological_only: true, gerekce: 'Anlam kaymış' });
      expect(call.headers.has('If-Match')).toBe(false);
      expect(await screen.findByTestId('etymology-saved')).toHaveTextContent(
        trLemma.kok.etym.saved(trLemma.kok.yes, trLemma.approval.editor),
      );
      await waitFor(() =>
        expect(fake.callsTo('get', '/api/v1/reviews/{id}').length).toBeGreaterThan(1),
      );
    });

    it.each([
      [400, 'dogrulama'],
      [409, 'durum-gecisi-gecersiz'],
      [412, 'surum-uyusmazligi'],
      [422, 'inceleme-desteklenmiyor'],
    ] as const)('shows %i in Turkish', async (status, kod) => {
      fake.post('/api/v1/lemmas/{id}/etimolojik-isaret', problem(status, kod));
      const { user } = setup({ route: '/?kayit=4', details: { 4: approved('editor') } });
      await card();
      await user.click(checkbox());
      fireEvent.change(reasonField(), { target: { value: 'Neden' } });
      await save(user);
      const alert = await screen.findByTestId('etymology-error');
      expect(alert).toHaveTextContent(trLemma.kok.etym.errors[status]);
      expect(reasonField()).toHaveValue('Neden');
    });
  });

  describe('the approval path filter', () => {
    const items = () => [
      kokItem(1),
      objectionItem(2, 'otomatik'),
      objectionItem(3, 'editor'),
      objectionItem(4, 'yeni-yol'),
    ];
    const openTab = async (user: User) => {
      await user.click(await screen.findByRole('tab', { name: trLemma.tabs.kok }));
      await screen.findByRole('link', { name: /^3001/ });
    };
    const pick = (user: User, label: string) =>
      user.click(screen.getByRole('radio', { name: label }));
    const links = () =>
      screen
        .getAllByRole('link')
        .map((link) => link.textContent ?? '')
        .filter((text) => /^300[0-9]/.test(text))
        .map((text) => text.slice(0, 4));

    it('shows the four options, "Hepsi" first, and says the server filters', async () => {
      const { user } = setup({ items: items() });
      await openTab(user);
      const group = screen.getByRole('radiogroup', { name: trLemma.approvalFilter.label });
      expect(
        within(group)
          .getAllByRole('radio')
          .map((radio) => radio.getAttribute('aria-label') ?? radio.parentElement?.textContent),
      ).toEqual([
        trLemma.approvalFilter.hepsi,
        trLemma.approvalFilter.otomatik,
        trLemma.approvalFilter.editor,
        trLemma.approvalFilter.aday,
      ]);
      expect(screen.getByRole('radio', { name: trLemma.approvalFilter.hepsi })).toBeChecked();
      expect(group).toHaveAccessibleDescription(new RegExp(trLemma.approvalFilter.note));
      expect(links()).toEqual(['3001', '3002', '3003', '3004']);
      // No client-side "yüklü sayfada süzülür" wording is left.
      expect(screen.queryByText(/yalnız yüklenen kayıtlara/)).not.toBeInTheDocument();
    });

    it('sends the choice to the server as onay_yolu in a new query (the cursor starts over)', async () => {
      const { user } = setup({ items: items() });
      await openTab(user);
      expect(listCalls().every((call) => !call.search.has('onay_yolu'))).toBe(true);
      await pick(user, trLemma.approvalFilter.otomatik);
      await waitFor(() => expect(links()).toEqual(['3002']));
      const call = listCalls().find((entry) => entry.search.get('onay_yolu') === 'otomatik')!;
      expect(call.search.get('hedef_tablo')).toBe('lemma');
      expect(call.search.get('alan')).toBe('kok_eslemesi');
      expect(call.search.has('cursor')).toBe(false);
      await pick(user, trLemma.approvalFilter.editor);
      await waitFor(() => expect(links()).toEqual(['3003']));
      expect(listCalls().some((entry) => entry.search.get('onay_yolu') === 'editor')).toBe(true);
      await pick(user, trLemma.approvalFilter.aday);
      await waitFor(() => expect(links()).toEqual(['3001']));
      expect(listCalls().some((entry) => entry.search.get('onay_yolu') === 'aday')).toBe(true);
      // "Hepsi" goes back to the request without the parameter.
      const before = listCalls().length;
      await pick(user, trLemma.approvalFilter.hepsi);
      await waitFor(() => expect(links()).toEqual(['3001', '3002', '3003', '3004']));
      expect(listCalls().length).toBeGreaterThanOrEqual(before);
      expect(listCalls().at(-1)!.search.has('onay_yolu')).toBe(false);
    });

    it('shows the normal empty state when the server finds no record of the path', async () => {
      const { user } = setup({ items: [kokItem(1), kokItem(2)] });
      await openTab(user);
      await pick(user, trLemma.approvalFilter.otomatik);
      expect(await screen.findByTestId('queue-empty')).toBeInTheDocument();
      expect(screen.queryByTestId('queue-filtered-empty')).not.toBeInTheDocument();
    });

    it('marks every row with its path from the list item: a badge for automatic and editor, text for the candidate', async () => {
      const { user } = setup({ items: items() });
      await openTab(user);
      const rows = screen.getAllByTestId('lemma-item-approval');
      expect(rows).toHaveLength(4);
      expect(rows[0]).toHaveTextContent(trLemma.approvalFilter.itemAday);
      expect(rows[0]!.querySelector('[data-testid="approval-badge"]')).toBeNull();
      expect(within(rows[1]!).getByTestId('approval-badge')).toHaveTextContent(
        trLemma.approval.otomatik,
      );
      expect(within(rows[2]!).getByTestId('approval-badge')).toHaveTextContent(
        trLemma.approval.editor,
      );
      // An objection whose path is unknown has no badge (and is in "Hepsi" only).
      expect(rows[3]!.querySelector('[data-testid="approval-badge"]')).toBeNull();
    });

    it('moves to the next visible record after a decision', async () => {
      const { user } = setup({
        items: items(),
        details: { 2: objectionDetail(2), 3: objectionDetail(3, 'editor') },
        route: '/?kayit=2',
      });
      await openTab(user);
      await pick(user, trLemma.approvalFilter.editor);
      await user.click(screen.getByRole('link', { name: /^3003/ }));
      await card();
      await user.click(await screen.findByRole('radio', { name: tr.review.approve }));
      fireEvent.change(screen.getByLabelText(tr.review.reason), { target: { value: 'Uygun' } });
      await user.click(screen.getByRole('button', { name: tr.review.submit }));
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(decisionCalls()[0]!.params.id).toBe('3');
    });
  });

  describe('accessibility', () => {
    const runAxe = (container: HTMLElement) =>
      axe.run(container, {
        rules: { 'color-contrast': { enabled: false }, 'target-size': { enabled: false } },
      });
    const names = (result: Awaited<ReturnType<typeof runAxe>>) =>
      result.violations.map(
        (violation) =>
          `${violation.id}: ${violation.nodes.map((node) => node.target.join(' ')).join(' | ')}`,
      );

    it('has no axe violations in the list with the approval path filter', async () => {
      const { container, user } = setup({
        items: [kokItem(1), objectionItem(2), objectionItem(3, 'editor')],
      });
      await user.click(await screen.findByRole('tab', { name: trLemma.tabs.kok }));
      await screen.findByRole('link', { name: /^3001/ });
      await user.click(screen.getByRole('radio', { name: trLemma.approvalFilter.otomatik }));
      expect(names(await runAxe(container))).toEqual([]);
    });

    it('has no axe violations on an automatic card with the open objection and etymology forms', async () => {
      const auto = kokDetail(4, {
        hedef: trTarget(4, { status: 'onayli', onay_yolu: 'otomatik' }),
      });
      const { container, user } = setup({ details: { 4: auto }, route: '/?kayit=4' });
      await card();
      await user.click(screen.getByRole('button', { name: trLemma.kok.objection.open }));
      await user.click(screen.getByRole('button', { name: trLemma.kok.objection.submit }));
      await screen.findByText(trLemma.kok.objection.reasonRequired);
      expect(names(await runAxe(container))).toEqual([]);
    });

    it('has no axe violations on a candidate card with the edit fields, the preview and the errors', async () => {
      const { container, user } = setup({ route: '/?kayit=1' });
      await card();
      await user.click(await screen.findByRole('radio', { name: tr.review.approve }));
      await screen.findByTestId('ar-lemma-preview');
      await user.click(screen.getByRole('button', { name: tr.review.submit }));
      await screen.findByTestId('decision-summary');
      expect(names(await runAxe(container))).toEqual([]);
    });

    it('draws every Arabic text with lang="ar" and dir="rtl"', async () => {
      setup({ route: '/?kayit=1' });
      await card();
      const arabic = [...document.querySelectorAll('[lang="ar"]')];
      expect(arabic.length).toBeGreaterThanOrEqual(2);
      for (const element of arabic) expect(element).toHaveAttribute('dir', 'rtl');
      // The meal context is Turkish, never marked Arabic.
      expect(screen.getAllByTestId('tr-kwic-item')[0]!.querySelector('[lang="ar"]')).toBeNull();
    });
  });

  it('keeps the fixture KWIC at three lines', () => {
    expect(TR_KWIC).toHaveLength(3);
  });
});
