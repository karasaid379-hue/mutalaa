// A18.4: the edit fields (Hedefi değiştir, Aralığı düzelt, Tür değiştir), the actions (uzmana gönder, ima, kalıp
// listesi), the answers' errors in Turkish and the role rules (editor, admin, uzman) of the link candidates queue.
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { components } from '@/api/schema';
import { tr } from '@/i18n/tr';
import { trBaglanti } from '@/i18n/tr-baglanti-sure';
import { BaglantiQueue } from '@/screens/baglanti/baglanti-queue';
import { ok, problem, useFakeApi, type Reply } from './fake-api';
import { linkTarget, unitFor, xrefDetail, xrefItem } from './fixtures-baglanti-sure';
import { page, session, stats } from './fixtures';
import { renderInRouter } from './render-app';

type Detail = components['schemas']['ReviewDetailDto'];

describe('link candidate edit and actions', () => {
  const fake = useFakeApi();
  const decisionCalls = () => fake.callsTo('post', '/api/v1/reviews/{id}/decision');
  const expertCalls = () => fake.callsTo('post', '/api/v1/reviews/{id}/uzmana-gonder');
  const imaCalls = () => fake.callsTo('post', '/api/v1/reviews/{id}/ima');
  const patternCalls = () => fake.callsTo('post', '/api/v1/reviews/{id}/kalip');
  const detailCalls = () => fake.callsTo('get', '/api/v1/reviews/{id}');

  interface Setup {
    roles?: string[];
    detail?: Detail;
    count?: number;
    route?: string;
  }

  /** The queue with `count` records and the detail of record 1 (or the given one); the handlers answer ok. */
  function setup({ roles = ['editor'], detail, count = 3, route = '/?kayit=1' }: Setup = {}) {
    const list = Array.from({ length: count }, (_, index) => xrefItem(index + 1));
    fake.get('/api/v1/reviews', ok(page(list)));
    fake.get('/api/v1/reviews/{id}', (call) => ok(detail ?? xrefDetail(Number(call.params.id))));
    fake.get('/api/v1/reviews/stats', ok(stats([['xref', 'status', count]])));
    fake.get('/api/v1/units/{anchor}', (call) => ok(unitFor(call.params.anchor!)));
    fake.get('/api/v1/auth/me', ok(session(roles)));
    fake.post('/api/v1/reviews/{id}/decision', (call) =>
      ok({
        id: Number(call.params.id),
        durum: 'onaylandi',
        eylem: 'duzenle_onayla',
        ikinci_onay_bekliyor: false,
        hedef_durumu: 'onayli',
        xmin: 700,
      }),
    );
    return renderInRouter(fake, <BaglantiQueue />, route);
  }

  const field = (name: string) => screen.findByLabelText(name);

  async function approveWith(user: ReturnType<typeof setup>['user'], reason = 'Uygun') {
    await user.click(await screen.findByRole('radio', { name: tr.review.approve }));
    fireEvent.change(screen.getByLabelText(tr.review.reason), { target: { value: reason } });
    await user.click(screen.getByRole('button', { name: tr.review.submit }));
  }

  describe('the edit fields', () => {
    it('shows the three fields with the current values and sends nothing when they stay empty', async () => {
      const { user } = setup();
      const box = await screen.findByTestId('link-edit');
      expect(within(box).getByLabelText(trBaglanti.edit.target)).toHaveValue('');
      expect(within(box).getByText(trBaglanti.edit.targetHint('q:1:2'))).toBeInTheDocument();
      expect(within(box).getByText(/Şu anki aralık: \[1, 5\)\./)).toBeInTheDocument();
      expect(
        within(box).getByText(trBaglanti.edit.typeCurrent(trBaglanti.types.iktibas)),
      ).toBeInTheDocument();
      await approveWith(user);
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(decisionCalls()[0]!.json).toEqual({
        karar: 'onaylandi',
        duzenlenen: null,
        gerekce: 'Uygun',
      });
    });

    it('changes the target: dst_anchor only, with If-Match', async () => {
      const { user } = setup();
      fireEvent.change(await field(trBaglanti.edit.target), { target: { value: 'q:2:255' } });
      await approveWith(user);
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      const call = decisionCalls()[0]!;
      expect(call.headers.get('If-Match')).toBe('"501"');
      expect(call.json).toEqual({
        karar: 'onaylandi',
        duzenlenen: { dst_anchor: 'q:2:255' },
        gerekce: 'Uygun',
      });
    });

    it('does not send a target equal to the current one', async () => {
      const { user } = setup();
      fireEvent.change(await field(trBaglanti.edit.target), { target: { value: ' q:1:2 ' } });
      await approveWith(user);
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect((decisionCalls()[0]!.json as { duzenlenen: unknown }).duzenlenen).toBeNull();
    });

    it('sends a target anchor that carries its own span without dst_span, and closes the span fields', async () => {
      const { user } = setup();
      const anchor = await field(trBaglanti.edit.target);
      fireEvent.change(anchor, { target: { value: 'q:2:255:3-7' } });
      const box = screen.getByTestId('link-edit');
      expect(within(box).getByLabelText(trBaglanti.edit.spanStart)).toBeDisabled();
      expect(within(box).getByLabelText(trBaglanti.edit.spanEnd)).toBeDisabled();
      fireEvent.blur(anchor);
      expect(
        within(box).getByText(trBaglanti.edit.spanCarried, { exact: false }),
      ).toBeInTheDocument();
      await approveWith(user);
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(decisionCalls()[0]!.json).toEqual({
        karar: 'onaylandi',
        duzenlenen: { dst_anchor: 'q:2:255:3-7' },
        gerekce: 'Uygun',
      });
    });

    it('sends the span typed in the two fields as [start, end] with the target', async () => {
      const { user } = setup();
      fireEvent.change(await field(trBaglanti.edit.target), { target: { value: 'q:2:255' } });
      fireEvent.change(screen.getByLabelText(trBaglanti.edit.spanStart), {
        target: { value: '2' },
      });
      fireEvent.change(screen.getByLabelText(trBaglanti.edit.spanEnd), { target: { value: '6' } });
      await approveWith(user);
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(decisionCalls()[0]!.json).toEqual({
        karar: 'onaylandi',
        duzenlenen: { dst_anchor: 'q:2:255', dst_span: [2, 6] },
        gerekce: 'Uygun',
      });
    });

    it('sends only the span when only the span is corrected', async () => {
      const { user } = setup();
      fireEvent.change(await field(trBaglanti.edit.spanStart), { target: { value: '3' } });
      fireEvent.change(screen.getByLabelText(trBaglanti.edit.spanEnd), { target: { value: '8' } });
      await approveWith(user);
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect((decisionCalls()[0]!.json as { duzenlenen: unknown }).duzenlenen).toEqual({
        dst_span: [3, 8],
      });
    });

    it.each([
      ['start is not smaller than end', '5', '5', trBaglanti.edit.problems.spanOrder],
      ['start is greater than end', '9', '4', trBaglanti.edit.problems.spanOrder],
      ['only the start is typed', '3', '', trBaglanti.edit.problems.spanBoth],
      ['a bound is not an integer', '3', '4,5', trBaglanti.edit.problems.spanInt],
      ['a bound has a sign', '-1', '4', trBaglanti.edit.problems.spanInt],
      ['a Quran word position is 0', '0', '4', trBaglanti.edit.problems.spanWordStart],
    ])(
      'blocks the approval when %s, with a message and without a request',
      async (_n, start, end, message) => {
        const { user } = setup();
        fireEvent.change(await field(trBaglanti.edit.spanStart), { target: { value: start } });
        fireEvent.change(screen.getByLabelText(trBaglanti.edit.spanEnd), {
          target: { value: end },
        });
        await approveWith(user);
        const summary = await screen.findByTestId('decision-summary');
        expect(within(summary).getByText(message)).toBeInTheDocument();
        expect(decisionCalls()).toHaveLength(0);
      },
    );

    it('accepts 0 as the start of a text target span (code points)', async () => {
      const { user } = setup({
        detail: xrefDetail(1, 'rn:deneme:p1', 'h:deneme:1', {
          hedef: linkTarget('rn:deneme:p1', 'h:deneme:1', { dst_span: [0, 3] }),
        }),
      });
      fireEvent.change(await field(trBaglanti.edit.spanStart), { target: { value: '0' } });
      fireEvent.change(screen.getByLabelText(trBaglanti.edit.spanEnd), { target: { value: '9' } });
      expect(screen.getByText(trBaglanti.edit.spanText, { exact: false })).toBeInTheDocument();
      await approveWith(user);
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect((decisionCalls()[0]!.json as { duzenlenen: unknown }).duzenlenen).toEqual({
        dst_span: [0, 9],
      });
    });

    it.each([
      ['an invalid anchor', 'q:2:287x', trBaglanti.edit.problems.anchorInvalid],
      ['an ayah range', 'q:2:255-257', trBaglanti.edit.problems.anchorRange],
      ['a sentence anchor', 'rn:deneme:p1:s2', trBaglanti.edit.problems.anchorSentence],
      ['a target that is no ayah or hadith', 'rn:deneme:p2', trBaglanti.edit.problems.anchorKind],
    ])(
      'blocks %s and says why (the anchor is read with @mutalaa/anchors)',
      async (_n, value, message) => {
        const { user } = setup();
        fireEvent.change(await field(trBaglanti.edit.target), { target: { value } });
        await approveWith(user);
        const summary = await screen.findByTestId('decision-summary');
        expect(within(summary).getByText(message)).toBeInTheDocument();
        expect(decisionCalls()).toHaveLength(0);
      },
    );

    it('accepts a hadith target', async () => {
      const { user } = setup();
      fireEvent.change(await field(trBaglanti.edit.target), { target: { value: 'h:buhari:52' } });
      await approveWith(user);
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect((decisionCalls()[0]!.json as { duzenlenen: unknown }).duzenlenen).toEqual({
        dst_anchor: 'h:buhari:52',
      });
    });

    it('changes the type among atif, iktibas and ima only (the current type is not offered again)', async () => {
      const { user } = setup();
      const group = await screen.findByRole('radiogroup', { name: trBaglanti.edit.type });
      const names = within(group)
        .getAllByRole('radio')
        .map((radio) => radio.closest('label')?.textContent);
      expect(names).toEqual([
        trBaglanti.edit.typeKeep,
        trBaglanti.types.atif,
        trBaglanti.types.ima,
      ]);
      await user.click(within(group).getByRole('radio', { name: trBaglanti.types.atif }));
      await approveWith(user);
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(decisionCalls()[0]!.json).toEqual({
        karar: 'onaylandi',
        duzenlenen: { type: 'atif' },
        gerekce: 'Uygun',
      });
    });

    it('can send the target, the span and the type together', async () => {
      const { user } = setup();
      fireEvent.change(await field(trBaglanti.edit.target), { target: { value: 'q:3:18' } });
      fireEvent.change(screen.getByLabelText(trBaglanti.edit.spanStart), {
        target: { value: '1' },
      });
      fireEvent.change(screen.getByLabelText(trBaglanti.edit.spanEnd), { target: { value: '4' } });
      await user.click(screen.getByRole('radio', { name: trBaglanti.types.ima }));
      await approveWith(user);
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect((decisionCalls()[0]!.json as { duzenlenen: unknown }).duzenlenen).toEqual({
        dst_anchor: 'q:3:18',
        dst_span: [1, 4],
        type: 'ima',
      });
    });

    it('does not offer a type change for a type that is fixed (kok, lemma, benzer_ayet)', async () => {
      setup({
        detail: xrefDetail(1, undefined, undefined, {
          hedef: linkTarget('rn:deneme:p1', 'q:1:2', { type: 'benzer_ayet' }),
        }),
      });
      const box = await screen.findByTestId('link-edit');
      expect(within(box).getByText(trBaglanti.edit.typeLocked)).toBeInTheDocument();
      expect(
        within(box).queryByRole('radiogroup', { name: trBaglanti.edit.type }),
      ).not.toBeInTheDocument();
    });

    it('sends no edit with a rejection, even when the fields are filled', async () => {
      const { user } = setup();
      fireEvent.change(await field(trBaglanti.edit.target), { target: { value: 'q:2:255' } });
      await user.click(await screen.findByRole('radio', { name: tr.review.reject }));
      fireEvent.change(screen.getByLabelText(tr.review.reason), { target: { value: 'Alakasız' } });
      await user.click(screen.getByRole('button', { name: tr.review.submit }));
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(decisionCalls()[0]!.json).toEqual({
        karar: 'reddedildi',
        duzenlenen: null,
        gerekce: 'Alakasız',
      });
    });

    it('moves on to the next record after an edited approval', async () => {
      const { user, router } = setup();
      fireEvent.change(await field(trBaglanti.edit.target), { target: { value: 'q:2:255' } });
      await approveWith(user);
      await waitFor(() => expect(router.state.location.search).toBe('?kayit=2'));
    });

    it.each<[string, Reply<never>, string, boolean]>([
      [
        '400 with the server detail',
        problem(400, 'dogrulama', { detail: 'dst_span kelime sinirlari disinda.' }),
        tr.problem.codes.dogrulama,
        false,
      ],
      ['403', problem(403, 'yetki-yok'), tr.problem.contexts.decision['yetki-yok'], false],
      ['404', problem(404, 'bulunamadi'), tr.problem.contexts.decision.bulunamadi, false],
      [
        '409',
        problem(409, 'durum-gecisi-gecersiz'),
        tr.problem.contexts.decision['durum-gecisi-gecersiz'],
        false,
      ],
      [
        '412',
        problem(412, 'surum-uyusmazligi'),
        tr.problem.contexts.decision['surum-uyusmazligi'],
        true,
      ],
      [
        '422 (a type change that is not allowed)',
        problem(422, 'inceleme-desteklenmiyor', { detail: 'tur degistirilemez.' }),
        tr.problem.codes['inceleme-desteklenmiyor'],
        false,
      ],
    ])(
      'shows the answer %s in Turkish and keeps the typed edit',
      async (_n, reply, title, refetches) => {
        const { user } = setup();
        fake.post('/api/v1/reviews/{id}/decision', reply);
        fireEvent.change(await field(trBaglanti.edit.target), { target: { value: 'q:2:255' } });
        await approveWith(user);
        expect(await screen.findByText(title)).toBeInTheDocument();
        expect(screen.getByLabelText(trBaglanti.edit.target)).toHaveValue('q:2:255');
        expect(screen.getByLabelText(tr.review.reason)).toHaveValue('Uygun');
        if (refetches) await waitFor(() => expect(detailCalls().length).toBeGreaterThan(1));
      },
    );

    it('shows the server detail of a 400 next to the Turkish title', async () => {
      const { user } = setup();
      fake.post(
        '/api/v1/reviews/{id}/decision',
        problem(400, 'dogrulama', { detail: 'dst_span kelime sinirlari disinda.' }),
      );
      fireEvent.change(await field(trBaglanti.edit.spanStart), { target: { value: '1' } });
      fireEvent.change(screen.getByLabelText(trBaglanti.edit.spanEnd), { target: { value: '99' } });
      await approveWith(user);
      expect(
        await screen.findByText(`${tr.problem.detail}: dst_span kelime sinirlari disinda.`),
      ).toBeInTheDocument();
    });
  });

  describe('the actions and the roles', () => {
    it.each([[['editor']], [['admin']], [['editor', 'admin']]])(
      'offers ima, pattern list and "Uzmana gönder" to the roles %j on an open record',
      async (roles) => {
        setup({ roles });
        const actions = await screen.findByTestId('link-actions');
        expect(
          within(actions).getByRole('button', { name: trBaglanti.actions.ima.open }),
        ).toBeInTheDocument();
        expect(
          within(actions).getByRole('button', { name: trBaglanti.actions.pattern.open }),
        ).toBeInTheDocument();
        expect(
          within(actions).getByRole('button', { name: trBaglanti.actions.expert.open }),
        ).toBeInTheDocument();
      },
    );

    it('offers no action to the expert role on an open record (and the decision form says why)', async () => {
      setup({ roles: ['uzman'] });
      expect(await screen.findByTestId('decision-role-note')).toHaveTextContent(tr.review.noRole);
      expect(screen.queryByTestId('link-actions')).not.toBeInTheDocument();
      expect(screen.queryByRole('radio', { name: tr.review.approve })).not.toBeInTheDocument();
    });

    it('offers no action for a record that is already with the expert', async () => {
      setup({ detail: xrefDetail(1, undefined, undefined, { durum: 'uzmanda' }) });
      await screen.findByTestId('link-card');
      await screen.findByTestId('decision-role-note');
      expect(screen.queryByTestId('link-actions')).not.toBeInTheDocument();
    });

    describe('Uzmana gönder', () => {
      it('requires a reason and sends nothing without it', async () => {
        const { user } = setup();
        await user.click(
          await screen.findByRole('button', { name: trBaglanti.actions.expert.open }),
        );
        await user.click(screen.getByRole('button', { name: trBaglanti.actions.expert.submit }));
        expect(await screen.findByText(trBaglanti.actions.reasonRequired)).toBeInTheDocument();
        expect(expertCalls()).toHaveLength(0);
      });

      it('sends {gerekce} with If-Match = xmin, then takes the record out and moves to the next one', async () => {
        fake.post('/api/v1/reviews/{id}/uzmana-gonder', (call) =>
          ok({
            id: Number(call.params.id),
            durum: 'uzmanda',
            eylem: 'uzmana_gonder',
            xmin: 900,
          }),
        );
        const { user, router } = setup();
        await user.click(
          await screen.findByRole('button', { name: trBaglanti.actions.expert.open }),
        );
        const section = screen.getByTestId('link-expert');
        fireEvent.change(within(section).getByLabelText(trBaglanti.actions.reason), {
          target: { value: 'Uzman görüşü gerekli' },
        });
        await user.click(
          within(section).getByRole('button', { name: trBaglanti.actions.expert.submit }),
        );
        await waitFor(() => expect(expertCalls()).toHaveLength(1));
        const call = expertCalls()[0]!;
        expect(call.params.id).toBe('1');
        expect(call.headers.get('If-Match')).toBe('"501"');
        expect(call.json).toEqual({ gerekce: 'Uzman görüşü gerekli' });
        await waitFor(() => expect(router.state.location.search).toBe('?kayit=2'));
      });

      it.each<[number, string, string]>([
        [403, 'yetki-yok', trBaglanti.actions.errors[403]!],
        [404, 'bulunamadi', trBaglanti.actions.errors[404]!],
        [409, 'durum-gecisi-gecersiz', trBaglanti.actions.errors[409]!],
        [422, 'inceleme-desteklenmiyor', trBaglanti.actions.errors[422]!],
      ])('shows the %s answer in Turkish and keeps the reason', async (status, kod, message) => {
        fake.post('/api/v1/reviews/{id}/uzmana-gonder', problem(status, kod));
        const { user } = setup();
        await user.click(
          await screen.findByRole('button', { name: trBaglanti.actions.expert.open }),
        );
        const section = screen.getByTestId('link-expert');
        fireEvent.change(within(section).getByLabelText(trBaglanti.actions.reason), {
          target: { value: 'Gerekçem' },
        });
        await user.click(
          within(section).getByRole('button', { name: trBaglanti.actions.expert.submit }),
        );
        expect(await within(section).findByTestId('link-expert-error')).toHaveTextContent(message);
        expect(within(section).getByLabelText(trBaglanti.actions.reason)).toHaveValue('Gerekçem');
      });

      it('shows the 412, reads the record again and keeps the reason', async () => {
        fake.post('/api/v1/reviews/{id}/uzmana-gonder', problem(412, 'surum-uyusmazligi'));
        const { user } = setup();
        await user.click(
          await screen.findByRole('button', { name: trBaglanti.actions.expert.open }),
        );
        const section = screen.getByTestId('link-expert');
        fireEvent.change(within(section).getByLabelText(trBaglanti.actions.reason), {
          target: { value: 'Gerekçem' },
        });
        const before = detailCalls().length;
        await user.click(
          within(section).getByRole('button', { name: trBaglanti.actions.expert.submit }),
        );
        expect(await within(section).findByTestId('link-expert-error')).toHaveTextContent(
          trBaglanti.actions.errors[412]!,
        );
        await waitFor(() => expect(detailCalls().length).toBeGreaterThan(before));
        expect(within(section).getByLabelText(trBaglanti.actions.reason)).toHaveValue('Gerekçem');
      });
    });

    describe('İma olarak işaretle', () => {
      it('sends {gerekce} without If-Match and says which ima row was opened; the candidate stays', async () => {
        fake.post('/api/v1/reviews/{id}/ima', (call) =>
          ok(
            {
              id: '00000000-0000-4000-8000-0000000000aa',
              review_id: Number(call.params.id),
              type: 'ima',
              status: 'onayli',
            },
            201,
          ),
        );
        const { user, router } = setup();
        await user.click(await screen.findByRole('button', { name: trBaglanti.actions.ima.open }));
        const section = screen.getByTestId('link-ima');
        fireEvent.change(within(section).getByLabelText(trBaglanti.actions.reason), {
          target: { value: 'Dolaylı gönderme' },
        });
        await user.click(
          within(section).getByRole('button', { name: trBaglanti.actions.ima.submit }),
        );
        await waitFor(() => expect(imaCalls()).toHaveLength(1));
        const call = imaCalls()[0]!;
        expect(call.params.id).toBe('1');
        expect(call.headers.has('If-Match')).toBe(false);
        expect(call.json).toEqual({ gerekce: 'Dolaylı gönderme' });
        expect(await within(section).findByTestId('link-ima-done')).toHaveTextContent(
          trBaglanti.actions.ima.done('00000000-0000-4000-8000-0000000000aa'),
        );
        // The candidate stays on screen: no move to the next record.
        expect(router.state.location.search).toBe('?kayit=1');
      });

      it.each<[number, string]>([
        [404, 'bulunamadi'],
        [409, 'cakisma'],
        [422, 'inceleme-desteklenmiyor'],
      ])('shows the %s answer in Turkish', async (status, kod) => {
        fake.post('/api/v1/reviews/{id}/ima', problem(status, kod));
        const { user } = setup();
        await user.click(await screen.findByRole('button', { name: trBaglanti.actions.ima.open }));
        const section = screen.getByTestId('link-ima');
        fireEvent.change(within(section).getByLabelText(trBaglanti.actions.reason), {
          target: { value: 'Gerekçem' },
        });
        await user.click(
          within(section).getByRole('button', { name: trBaglanti.actions.ima.submit }),
        );
        expect(await within(section).findByTestId('link-ima-error')).toHaveTextContent(
          trBaglanti.actions.errors[status]!,
        );
      });

      it('shows a 400 as the generic validation problem', async () => {
        fake.post(
          '/api/v1/reviews/{id}/ima',
          problem(400, 'dogrulama', { detail: 'gerekce bos.' }),
        );
        const { user } = setup();
        await user.click(await screen.findByRole('button', { name: trBaglanti.actions.ima.open }));
        const section = screen.getByTestId('link-ima');
        fireEvent.change(within(section).getByLabelText(trBaglanti.actions.reason), {
          target: { value: 'Gerekçem' },
        });
        await user.click(
          within(section).getByRole('button', { name: trBaglanti.actions.ima.submit }),
        );
        expect(await within(section).findByText(tr.problem.codes.dogrulama)).toBeInTheDocument();
      });
    });

    describe('Kalıp listesine ekle', () => {
      it('sends {gerekce} with If-Match, says the key and moves to the next record (the candidate is rejected)', async () => {
        fake.post('/api/v1/reviews/{id}/kalip', (call) =>
          ok({
            id: Number(call.params.id),
            durum: 'reddedildi',
            eylem: 'kalip_ekle',
            xmin: 950,
            anahtar: 'deneme-kalip-1',
            denetim_review_id: 77,
          }),
        );
        const { user, router } = setup();
        await user.click(
          await screen.findByRole('button', { name: trBaglanti.actions.pattern.open }),
        );
        const section = screen.getByTestId('link-pattern');
        fireEvent.change(within(section).getByLabelText(trBaglanti.actions.reason), {
          target: { value: 'Kalıp ifade' },
        });
        await user.click(
          within(section).getByRole('button', { name: trBaglanti.actions.pattern.submit }),
        );
        await waitFor(() => expect(patternCalls()).toHaveLength(1));
        const call = patternCalls()[0]!;
        expect(call.headers.get('If-Match')).toBe('"501"');
        expect(call.json).toEqual({ gerekce: 'Kalıp ifade' });
        await waitFor(() => expect(router.state.location.search).toBe('?kayit=2'));
      });

      it.each<[number, string]>([
        [403, 'yetki-yok'],
        [404, 'bulunamadi'],
        [409, 'durum-gecisi-gecersiz'],
        [412, 'surum-uyusmazligi'],
        [422, 'inceleme-desteklenmiyor'],
      ])('shows the %s answer in Turkish and keeps the reason', async (status, kod) => {
        fake.post('/api/v1/reviews/{id}/kalip', problem(status, kod));
        const { user } = setup();
        await user.click(
          await screen.findByRole('button', { name: trBaglanti.actions.pattern.open }),
        );
        const section = screen.getByTestId('link-pattern');
        fireEvent.change(within(section).getByLabelText(trBaglanti.actions.reason), {
          target: { value: 'Gerekçem' },
        });
        await user.click(
          within(section).getByRole('button', { name: trBaglanti.actions.pattern.submit }),
        );
        expect(await within(section).findByTestId('link-pattern-error')).toHaveTextContent(
          trBaglanti.actions.errors[status]!,
        );
        expect(within(section).getByLabelText(trBaglanti.actions.reason)).toHaveValue('Gerekçem');
      });
    });
  });

  describe('a record at the expert', () => {
    const atExpert = () => xrefDetail(1, undefined, undefined, { durum: 'uzmanda' });

    it.each([[['editor']], [['admin']], [['editor', 'admin']]])(
      'shows "Uzman kararı bekleniyor" and no decision buttons to the roles %j',
      async (roles) => {
        setup({ roles, detail: atExpert() });
        expect(await screen.findByTestId('decision-role-note')).toHaveTextContent(
          tr.review.expertPending,
        );
        expect(screen.queryByRole('radio', { name: tr.review.approve })).not.toBeInTheDocument();
        expect(screen.queryByRole('radio', { name: tr.review.reject })).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: tr.review.submit })).not.toBeInTheDocument();
      },
    );

    it('opens approval and rejection to the expert role only, and the expert decides with If-Match', async () => {
      const { user } = setup({ roles: ['uzman'], detail: atExpert() });
      expect(await screen.findByRole('radio', { name: tr.review.approve })).toBeEnabled();
      expect(screen.getByRole('radio', { name: tr.review.reject })).toBeEnabled();
      expect(screen.queryByTestId('decision-role-note')).not.toBeInTheDocument();
      await approveWith(user, 'Uzman onayı');
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(decisionCalls()[0]!.headers.get('If-Match')).toBe('"501"');
      expect(decisionCalls()[0]!.json).toEqual({
        karar: 'onaylandi',
        duzenlenen: null,
        gerekce: 'Uzman onayı',
      });
    });

    it('shows the 403 yetki-yok of the server in Turkish when the decision is refused', async () => {
      // The panel hides buttons by role, but the server has the last word; a 403 on the decision is worded.
      const { user } = setup({ roles: ['uzman'], detail: atExpert() });
      fake.post('/api/v1/reviews/{id}/decision', problem(403, 'yetki-yok'));
      await approveWith(user, 'Uzman onayı');
      expect(
        await screen.findByText(tr.problem.contexts.decision['yetki-yok']),
      ).toBeInTheDocument();
    });
  });
});
