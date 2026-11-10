import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { DecisionForm } from '@/review/decision-form';
import { tr } from '@/i18n/tr';
import type { components } from '@/api/schema';
import { ok, problem, useFakeApi } from './fake-api';
import { EDITOR_EMAIL, OTHER_EMAIL, reviewDetail, session, unitDetail } from './fixtures';
import { renderWithProviders } from './render-app';

type Detail = components['schemas']['ReviewDetailDto'];
type Unit = components['schemas']['UnitDetail'];

const DECIDED = {
  id: 1,
  durum: 'onaylandi',
  eylem: 'onayla',
  ikinci_onay_bekliyor: false,
  hedef_durumu: 'onayli',
  xmin: 101,
};

describe('DecisionForm', () => {
  const fake = useFakeApi();

  function setup(
    review: Detail = reviewDetail(),
    options: {
      unit?: Unit;
      email?: string;
      onDecided?: () => void;
      decision?: typeof DECIDED;
    } = {},
  ) {
    fake.get('/api/v1/auth/me', ok(session(['editor'], options.email ?? EDITOR_EMAIL)));
    fake.get('/api/v1/units/{anchor}', ok(options.unit ?? unitDetail()));
    fake.post('/api/v1/reviews/{id}/decision', ok(options.decision ?? DECIDED));
    const onDecided = options.onDecided ?? vi.fn();
    const view = renderWithProviders(fake, <DecisionForm review={review} onDecided={onDecided} />);
    return { ...view, onDecided };
  }

  const approve = () => screen.getByRole('radio', { name: tr.review.approve });
  const reject = () => screen.getByRole('radio', { name: tr.review.reject });
  const reason = () => screen.getByLabelText(tr.review.reason);
  const submit = () => screen.getByRole('button', { name: tr.review.submit });
  const decisionCalls = () => fake.callsTo('post', '/api/v1/reviews/{id}/decision');

  describe('validation', () => {
    it('asks for an explicit choice and a reason, sends nothing and focuses the summary', async () => {
      const { user } = setup();
      await user.click(submit());
      const summary = await screen.findByTestId('decision-summary');
      expect(within(summary).getByText(tr.review.chooseDecision)).toBeInTheDocument();
      expect(within(summary).getByText(tr.review.reasonRequired)).toBeInTheDocument();
      expect(decisionCalls()).toHaveLength(0);
      await waitFor(() => expect(summary.parentElement).toHaveFocus());
      // Neither option is pre-selected.
      expect(approve()).not.toBeChecked();
      expect(reject()).not.toBeChecked();
    });

    it('requires a non-blank reason', async () => {
      const { user } = setup();
      await user.click(approve());
      fireEvent.change(reason(), { target: { value: '   ' } });
      await user.click(submit());
      expect(await screen.findByText(tr.review.reasonRequired)).toBeInTheDocument();
      expect(decisionCalls()).toHaveLength(0);
    });

    it('limits the reason to 2000 code points (not UTF-16 units)', async () => {
      const { user } = setup();
      await user.click(approve());
      fireEvent.change(reason(), { target: { value: 'a'.repeat(2001) } });
      await user.click(submit());
      expect(await screen.findByText(tr.review.reasonTooLong(2001, 2000))).toBeInTheDocument();
      expect(decisionCalls()).toHaveLength(0);

      // 1001 astral characters are 2002 UTF-16 units but 1001 code points: allowed.
      fireEvent.change(reason(), { target: { value: '\u{1F600}'.repeat(1001) } });
      await user.click(submit());
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
    });

    it('accepts exactly 2000 code points', async () => {
      const { user } = setup();
      await user.click(approve());
      fireEvent.change(reason(), { target: { value: 'b'.repeat(2000) } });
      await user.click(submit());
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect((decisionCalls()[0]?.json as { gerekce: string }).gerekce).toHaveLength(2000);
    });

    it('warns about NUL and lone surrogates, blocks the send and cleans only on the button', async () => {
      const { user } = setup();
      await user.click(approve());
      const dirty = 'Gerekçe\u0000 metni\uD800';
      fireEvent.change(reason(), { target: { value: dirty } });
      expect(await screen.findByTestId('unwritable-warning')).toBeInTheDocument();
      await user.click(submit());
      expect(
        await screen.findByText(`${tr.review.reason}: ${tr.review.unwritable}`),
      ).toBeInTheDocument();
      expect(decisionCalls()).toHaveLength(0);
      // Nothing was cleaned silently.
      expect((reason() as HTMLTextAreaElement).value).toBe(dirty);

      await user.click(screen.getByRole('button', { name: tr.review.unwritableAction }));
      expect((reason() as HTMLTextAreaElement).value).toBe('Gerekçe metni');
      expect(screen.queryByTestId('unwritable-warning')).not.toBeInTheDocument();
      await user.click(submit());
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect((decisionCalls()[0]?.json as { gerekce: string }).gerekce).toBe('Gerekçe metni');
    });
  });

  describe('request', () => {
    it('sends If-Match "{xmin}" and the body {karar, duzenlenen, gerekce}', async () => {
      const { user, onDecided } = setup(reviewDetail({ id: 7, xmin: 4294967295 }));
      await user.click(approve());
      await user.type(reason(), 'Kaynakla karşılaştırıldı');
      await user.click(submit());
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      const call = decisionCalls()[0]!;
      expect(call.params.id).toBe('7');
      expect(call.headers.get('If-Match')).toBe('"4294967295"');
      expect(call.json).toEqual({
        karar: 'onaylandi',
        duzenlenen: null,
        gerekce: 'Kaynakla karşılaştırıldı',
      });
      expect(Object.keys(call.json as object).sort()).toEqual(['duzenlenen', 'gerekce', 'karar']);
      await waitFor(() => expect(onDecided).toHaveBeenCalledTimes(1));
      expect(onDecided).toHaveBeenCalledWith(DECIDED, 'onaylandi');
    });

    it('sends a rejection with duzenlenen null', async () => {
      const { user } = setup();
      await user.click(reject());
      await user.type(reason(), 'Hatalı');
      await user.click(submit());
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(decisionCalls()[0]?.json).toEqual({
        karar: 'reddedildi',
        duzenlenen: null,
        gerekce: 'Hatalı',
      });
    });

    it('sends with Ctrl+Enter and Meta+Enter from the reason field', async () => {
      const { user } = setup();
      await user.click(reject());
      await user.type(reason(), 'Kısayol');
      await user.keyboard('{Control>}{Enter}{/Control}');
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
    });

    it('announces the decision in the live region and shows it in the form', async () => {
      const { user } = setup();
      await user.click(approve());
      await user.type(reason(), 'Tamam');
      await user.click(submit());
      expect(await screen.findByTestId('decision-done')).toHaveTextContent(
        tr.review.decided('onaylandi'),
      );
      expect(screen.getByRole('status')).toHaveTextContent(tr.review.decided('onaylandi'));
      expect(submit()).toBeDisabled();
    });

    it('says when the record now waits for its second approval', async () => {
      const { user } = setup(reviewDetail(), {
        decision: {
          ...DECIDED,
          durum: 'acik',
          ikinci_onay_bekliyor: true,
          hedef_durumu: 'incelemede',
        },
      });
      await user.click(approve());
      await user.type(reason(), 'Birinci onay');
      await user.click(submit());
      expect(await screen.findByTestId('decision-done')).toHaveTextContent(tr.review.secondPending);
    });

    it('shows other API errors with their message and focuses them', async () => {
      const { user } = setup();
      fake.post(
        '/api/v1/reviews/{id}/decision',
        problem(422, 'inceleme-desteklenmiyor', {
          detail:
            "Ofsetli alanlar (marks, sentences) metin degisimini A16'da hesaplanana kadar desteklenmiyor.",
        }),
      );
      await user.click(approve());
      await user.type(reason(), 'Dene');
      await user.click(submit());
      const message = await screen.findByText(tr.problem.offsetUnsupported);
      await waitFor(() => expect(message.closest('[role="alert"]')?.parentElement).toHaveFocus());
    });

    it('shows a 409 with the server message', async () => {
      const { user } = setup();
      fake.post(
        '/api/v1/reviews/{id}/decision',
        problem(409, 'durum-gecisi-gecersiz', { detail: 'Editor kendi onerisini onaylayamaz.' }),
      );
      await user.click(approve());
      await user.type(reason(), 'Dene');
      await user.click(submit());
      expect(
        await screen.findByText(tr.problem.contexts.decision['durum-gecisi-gecersiz']),
      ).toBeInTheDocument();
      expect(
        screen.getByText(`${tr.problem.detail}: Editor kendi onerisini onaylayamaz.`),
      ).toBeInTheDocument();
    });
  });

  describe('edited text', () => {
    it('has no edit field until approve is chosen, then shows the proposed text', async () => {
      const { user } = setup();
      await screen.findByRole('radiogroup');
      expect(screen.queryByLabelText(tr.review.editedText)).not.toBeInTheDocument();
      await user.click(approve());
      const field = (await screen.findByLabelText(tr.review.editedText)) as HTMLTextAreaElement;
      expect(field.value).toBe('Deneme paragrafı 1 düzeltilmiş');
      await user.click(reject());
      expect(screen.queryByLabelText(tr.review.editedText)).not.toBeInTheDocument();
    });

    it('sends duzenlenen only when the text was changed', async () => {
      const { user } = setup();
      await user.click(approve());
      await screen.findByLabelText(tr.review.editedText);
      await user.type(reason(), 'Düzeltildi');
      await user.click(submit());
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect((decisionCalls()[0]?.json as { duzenlenen: unknown }).duzenlenen).toBeNull();
    });

    it('sends {metin} when the editor changed the text', async () => {
      const { user } = setup();
      await user.click(approve());
      const field = await screen.findByLabelText(tr.review.editedText);
      fireEvent.change(field, { target: { value: 'Deneme paragrafı 1 elle düzeltildi' } });
      await user.type(reason(), 'Elle düzeltildi');
      await user.click(submit());
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(decisionCalls()[0]?.json).toEqual({
        karar: 'onaylandi',
        duzenlenen: { metin: 'Deneme paragrafı 1 elle düzeltildi' },
        gerekce: 'Elle düzeltildi',
      });
    });

    it('rejects NUL in the edited text before sending', async () => {
      const { user } = setup();
      await user.click(approve());
      const field = await screen.findByLabelText(tr.review.editedText);
      fireEvent.change(field, { target: { value: 'Deneme\u0000 metni' } });
      await user.type(reason(), 'Dene');
      await user.click(submit());
      expect(
        await screen.findByText(`${tr.review.editedText}: ${tr.review.unwritable}`),
      ).toBeInTheDocument();
      expect(decisionCalls()).toHaveLength(0);
      await user.click(screen.getByRole('button', { name: tr.review.unwritableAction }));
      expect((field as HTMLTextAreaElement).value).toBe('Deneme metni');
    });

    it.each([
      [
        'an ayet (Tanzil) unit',
        unitDetail({ kind: 'ayet', kaynak_tur: 'kuran_metni', duzeltilebilir: false }),
      ],
      ['a unit with offset data', unitDetail({ marks: [[0, 2, 'x']] })],
      ['a unit the API does not allow to correct', unitDetail({ duzeltilebilir: false })],
    ])('has no edit field for %s', async (_, unit) => {
      const { user } = setup(reviewDetail(), { unit });
      await waitFor(() => expect(fake.callsTo('get', '/api/v1/units/{anchor}')).toHaveLength(1));
      await user.click(approve());
      expect(screen.queryByLabelText(tr.review.editedText)).not.toBeInTheDocument();
    });

    it('has no edit field in the second approval stage and says why', async () => {
      const review = reviewDetail({
        ikinci_onay_bekliyor: true,
        inceleyen: OTHER_EMAIL,
        koken: 'hat',
      });
      const { user } = setup(review);
      await user.click(approve());
      expect(screen.queryByLabelText(tr.review.editedText)).not.toBeInTheDocument();
      expect(screen.getByText(tr.review.secondStageNote)).toBeInTheDocument();
    });

    it('does not ask for the unit when the review is not a unit text', async () => {
      setup(reviewDetail({ hedef_tablo: 'xref', hedef_anahtar: 'x', alan: 'status' }));
      await screen.findByRole('radiogroup');
      expect(fake.callsTo('get', '/api/v1/units/{anchor}')).toHaveLength(0);
    });
  });

  describe('closed in advance', () => {
    it('closes "Onayla" for the editor\'s own proposal but keeps reject', async () => {
      const { user } = setup(reviewDetail({ koken: 'editor', oneren: EDITOR_EMAIL }));
      expect(await screen.findByTestId('approve-closed-reason')).toHaveTextContent(
        tr.review.blockedOwnProposal,
      );
      expect(approve()).toHaveAttribute('aria-disabled', 'true');
      expect(reject()).not.toHaveAttribute('aria-disabled', 'true');
      await user.click(reject());
      await user.type(reason(), 'Kendi önerim, geri çekiyorum');
      await user.click(submit());
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect((decisionCalls()[0]?.json as { karar: string }).karar).toBe('reddedildi');
    });

    it('closes the second approval for the first approver', async () => {
      setup(reviewDetail({ ikinci_onay_bekliyor: true, inceleyen: EDITOR_EMAIL, koken: 'hat' }));
      expect(await screen.findByTestId('approve-closed-reason')).toHaveTextContent(
        tr.review.blockedSameFirstApprover,
      );
      expect(approve()).toHaveAttribute('aria-disabled', 'true');
    });

    it('leaves "Onayla" open for a pipeline proposal', async () => {
      setup(reviewDetail({ koken: 'hat', oneren: 'hat' }));
      await screen.findByRole('radiogroup');
      expect(screen.queryByTestId('approve-closed-reason')).not.toBeInTheDocument();
      expect(approve()).not.toHaveAttribute('aria-disabled', 'true');
    });

    it('closes the whole form for a decided record', async () => {
      setup(reviewDetail({ durum: 'onaylandi' }));
      expect(await screen.findByText(tr.review.closedTitle)).toBeInTheDocument();
      expect(submit()).toBeDisabled();
      expect(reason()).toBeDisabled();
    });
  });

  describe('412 (the record changed)', () => {
    it('fetches the record again, shows the field difference and the text diff, keeps the input and does not resend', async () => {
      const original = reviewDetail({ id: 5, xmin: 100 });
      const fresh = reviewDetail({
        id: 5,
        xmin: 101,
        onerilen: { metin: 'Deneme paragrafı 1 başka düzeltme', content_hash: 'hash-9' },
        inceleyen: null,
      });
      const { user, onDecided } = setup(original);
      fake.post('/api/v1/reviews/{id}/decision', problem(412, 'surum-uyusmazligi'));
      fake.get('/api/v1/reviews/{id}', ok(fresh));

      await user.click(approve());
      const edited = await screen.findByLabelText(tr.review.editedText);
      fireEvent.change(edited, { target: { value: 'Benim düzeltmem' } });
      await user.type(reason(), 'Kayıt değişmeden önce yazdım');
      await user.click(submit());

      const stale = await screen.findByTestId('stale-record');
      expect(within(stale).getByText(tr.review.stale.title)).toBeInTheDocument();
      // The changed field and the word level text difference.
      expect(
        within(stale).getByText(tr.labels.reviewField.onerilen, { selector: 'th' }),
      ).toBeInTheDocument();
      const diff = within(stale).getByTestId('text-diff');
      expect(diff.querySelector('ins')?.textContent).toMatch(/başka/);
      expect(diff.querySelector('del')?.textContent).toMatch(/düzeltilmiş/);

      // The record was fetched once, nothing was resent, the input is intact.
      expect(fake.callsTo('get', '/api/v1/reviews/{id}')).toHaveLength(1);
      expect(decisionCalls()).toHaveLength(1);
      expect(onDecided).not.toHaveBeenCalled();
      expect(approve()).toBeChecked();
      expect((screen.getByLabelText(tr.review.editedText) as HTMLTextAreaElement).value).toBe(
        'Benim düzeltmem',
      );
      expect((reason() as HTMLTextAreaElement).value).toBe('Kayıt değişmeden önce yazdım');

      // The editor resends by hand: the fresh version is in If-Match.
      fake.post('/api/v1/reviews/{id}/decision', ok(DECIDED));
      await user.click(submit());
      await waitFor(() => expect(decisionCalls()).toHaveLength(2));
      expect(decisionCalls()[1]?.headers.get('If-Match')).toBe('"101"');
      expect(decisionCalls()[0]?.headers.get('If-Match')).toBe('"100"');
      expect((decisionCalls()[1]?.json as { duzenlenen: unknown }).duzenlenen).toEqual({
        metin: 'Benim düzeltmem',
      });
    });

    it('tells that only the version moved when no visible field differs', async () => {
      const { user } = setup(reviewDetail({ xmin: 100 }));
      fake.post('/api/v1/reviews/{id}/decision', problem(412, 'surum-uyusmazligi'));
      fake.get('/api/v1/reviews/{id}', ok(reviewDetail({ xmin: 101 })));
      await user.click(reject());
      await user.type(reason(), 'Ret');
      await user.click(submit());
      const stale = await screen.findByTestId('stale-record');
      expect(within(stale).getByText(tr.review.stale.noFieldChange)).toBeInTheDocument();
    });

    it('says when the record is no longer open', async () => {
      const { user } = setup(reviewDetail({ xmin: 100 }));
      fake.post('/api/v1/reviews/{id}/decision', problem(412, 'surum-uyusmazligi'));
      fake.get(
        '/api/v1/reviews/{id}',
        ok(reviewDetail({ xmin: 101, durum: 'reddedildi', eylem: 'reddet' })),
      );
      await user.click(approve());
      await user.type(reason(), 'Onay');
      await user.click(submit());
      const stale = await screen.findByTestId('stale-record');
      expect(within(stale).getByText(tr.review.stale.closedNow)).toBeInTheDocument();
      await waitFor(() => expect(submit()).toBeDisabled());
    });

    it('shows the problem when the refresh itself fails', async () => {
      const { user } = setup(reviewDetail({ xmin: 100 }));
      fake.post('/api/v1/reviews/{id}/decision', problem(412, 'surum-uyusmazligi'));
      fake.get('/api/v1/reviews/{id}', problem(404, 'bulunamadi'));
      await user.click(approve());
      await user.type(reason(), 'Onay');
      await user.click(submit());
      expect(await screen.findByText(tr.problem.contexts.decision.bulunamadi)).toBeInTheDocument();
      expect(screen.queryByTestId('stale-record')).not.toBeInTheDocument();
    });
  });
});
