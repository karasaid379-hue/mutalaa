// A18 review fixes on the link candidates queue: the edit fields close and empty when the anchor carries its own
// span, the action forms move focus and announce errors, and a re-validation record (an approved link asked again)
// has its own words, hides the edit, ima and pattern actions and cannot be selected for the bulk approval.
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import axe from 'axe-core';
import { describe, expect, it } from 'vitest';
import type { components } from '@/api/schema';
import { tr } from '@/i18n/tr';
import { trBaglanti } from '@/i18n/tr-baglanti-sure';
import { BaglantiQueue } from '@/screens/baglanti/baglanti-queue';
import { ok, problem, useFakeApi } from './fake-api';
import { linkTarget, unitFor, xrefDetail, xrefItem } from './fixtures-baglanti-sure';
import { page, session, stats } from './fixtures';
import { renderInRouter } from './render-app';

type Detail = components['schemas']['ReviewDetailDto'];
type Item = components['schemas']['ReviewItemDto'];

const REVALIDATION = { yeniden_dogrula: true };

/** A re-validation record: an approved link (`hedef.status = onayli`) whose proposal asks to confirm it again. */
function revalidationDetail(id = 1): Detail {
  return xrefDetail(id, undefined, undefined, {
    onerilen: REVALIDATION,
    hedef: linkTarget('rn:deneme:p1', 'q:1:2', { status: 'onayli' }),
  });
}

async function violations(container: Element): Promise<string[]> {
  const result = await axe.run(container, {
    rules: { 'color-contrast': { enabled: false }, 'target-size': { enabled: false } },
  });
  return result.violations.map((violation) => violation.id);
}

describe('link candidates: A18 review fixes', () => {
  const fake = useFakeApi();
  const decisionCalls = () => fake.callsTo('post', '/api/v1/reviews/{id}/decision');

  interface Setup {
    roles?: string[];
    detail?: Detail;
    items?: Item[];
    route?: string;
  }

  function setup({ roles = ['editor'], detail, items, route = '/?kayit=1' }: Setup = {}) {
    const list = items ?? [xrefItem(1), xrefItem(2)];
    fake.get('/api/v1/reviews', ok(page(list)));
    fake.get('/api/v1/reviews/{id}', (call) => ok(detail ?? xrefDetail(Number(call.params.id))));
    fake.get('/api/v1/reviews/stats', ok(stats([['xref', 'status', list.length]])));
    fake.get('/api/v1/units/{anchor}', (call) => ok(unitFor(call.params.anchor!)));
    fake.get('/api/v1/auth/me', ok(session(roles)));
    fake.post('/api/v1/reviews/{id}/decision', (call) =>
      ok({
        id: Number(call.params.id),
        durum: 'onaylandi',
        eylem: 'onayla',
        ikinci_onay_bekliyor: false,
        hedef_durumu: 'onayli',
        xmin: 700,
      }),
    );
    return renderInRouter(fake, <BaglantiQueue />, route);
  }

  describe('an anchor that carries its own span', () => {
    const startField = () => screen.getByLabelText(trBaglanti.edit.spanStart);
    const endField = () => screen.getByLabelText(trBaglanti.edit.spanEnd);

    it('empties the span fields that were typed, closes them and says why', async () => {
      const { user } = setup();
      const box = await screen.findByTestId('link-edit');
      fireEvent.change(startField(), { target: { value: '2' } });
      fireEvent.change(endField(), { target: { value: '6' } });
      expect(startField()).toHaveValue('2');
      fireEvent.change(within(box).getByLabelText(trBaglanti.edit.target), {
        target: { value: 'q:2:255:3-7' },
      });
      expect(startField()).toHaveValue('');
      expect(endField()).toHaveValue('');
      expect(startField()).toBeDisabled();
      expect(endField()).toBeDisabled();
      // The reason is in a status area, so it is announced when the fields close.
      expect(within(box).getByRole('status')).toHaveTextContent(trBaglanti.edit.spanCarried);
      // The approval is not blocked by the closed fields, and nothing but the anchor is sent.
      await user.click(screen.getByRole('radio', { name: tr.review.approve }));
      fireEvent.change(screen.getByLabelText(tr.review.reason), { target: { value: 'Uygun' } });
      await user.click(screen.getByRole('button', { name: tr.review.submit }));
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(decisionCalls()[0]!.json).toEqual({
        karar: 'onaylandi',
        duzenlenen: { dst_anchor: 'q:2:255:3-7' },
        gerekce: 'Uygun',
      });
    });

    it('empties the fields for a span written with @ too, and opens them again for a plain anchor', async () => {
      setup();
      const box = await screen.findByTestId('link-edit');
      const target = within(box).getByLabelText(trBaglanti.edit.target);
      fireEvent.change(startField(), { target: { value: '1' } });
      fireEvent.change(endField(), { target: { value: '4' } });
      fireEvent.change(target, { target: { value: 'h:buhari:52@3-9' } });
      expect(startField()).toHaveValue('');
      expect(startField()).toBeDisabled();
      fireEvent.change(target, { target: { value: 'q:2:255' } });
      expect(startField()).toBeEnabled();
      expect(endField()).toBeEnabled();
      // The emptied values do not come back; the status area is empty again.
      expect(startField()).toHaveValue('');
      expect(within(box).getByRole('status')).toBeEmptyDOMElement();
    });

    it('does not block an approval with a leftover span: the form holds no conflict', async () => {
      const { user } = setup();
      const box = await screen.findByTestId('link-edit');
      fireEvent.change(startField(), { target: { value: '3' } });
      fireEvent.change(endField(), { target: { value: '8' } });
      fireEvent.change(within(box).getByLabelText(trBaglanti.edit.target), {
        target: { value: 'q:2:255:2-5' },
      });
      await user.click(screen.getByRole('radio', { name: tr.review.approve }));
      fireEvent.change(screen.getByLabelText(tr.review.reason), { target: { value: 'Uygun' } });
      await user.click(screen.getByRole('button', { name: tr.review.submit }));
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(screen.queryByText(trBaglanti.edit.problems.spanConflict)).not.toBeInTheDocument();
    });
  });

  describe('the edit fields after a failed submit', () => {
    it('moves focus to the error summary and ties the field to its message', async () => {
      const { user } = setup();
      const box = await screen.findByTestId('link-edit');
      const target = within(box).getByLabelText(trBaglanti.edit.target);
      fireEvent.change(target, { target: { value: 'q:2:287x' } });
      await user.click(screen.getByRole('radio', { name: tr.review.approve }));
      fireEvent.change(screen.getByLabelText(tr.review.reason), { target: { value: 'Uygun' } });
      await user.click(screen.getByRole('button', { name: tr.review.submit }));
      const summary = await screen.findByTestId('decision-summary');
      expect(summary).toHaveAttribute('role', 'alert');
      expect(summary.parentElement).toHaveFocus();
      // Without leaving the field: the field is invalid and describes itself with the summary item.
      expect(target).toHaveAttribute('aria-invalid', 'true');
      expect(target).toHaveAccessibleDescription(
        new RegExp(trBaglanti.edit.problems.anchorInvalid),
      );
      await user.click(
        within(summary).getByRole('link', { name: trBaglanti.edit.problems.anchorInvalid }),
      );
      expect(target).toHaveFocus();
    });

    it('marks the two span fields invalid and the link focuses the first', async () => {
      const { user } = setup();
      const start = await screen.findByLabelText(trBaglanti.edit.spanStart);
      fireEvent.change(start, { target: { value: '5' } });
      fireEvent.change(screen.getByLabelText(trBaglanti.edit.spanEnd), { target: { value: '5' } });
      await user.click(screen.getByRole('radio', { name: tr.review.approve }));
      fireEvent.change(screen.getByLabelText(tr.review.reason), { target: { value: 'Uygun' } });
      await user.click(screen.getByRole('button', { name: tr.review.submit }));
      const summary = await screen.findByTestId('decision-summary');
      expect(start).toHaveAttribute('aria-invalid', 'true');
      expect(screen.getByLabelText(trBaglanti.edit.spanEnd)).toHaveAttribute(
        'aria-invalid',
        'true',
      );
      await user.click(
        within(summary).getByRole('link', { name: trBaglanti.edit.problems.spanOrder }),
      );
      expect(start).toHaveFocus();
    });
  });

  describe('the action forms: focus and errors', () => {
    const section = (testId: string) => screen.getByTestId(testId);
    const openButton = (name: string) => screen.findByRole('button', { name });
    const reasonOf = (testId: string) =>
      within(section(testId)).getByLabelText(trBaglanti.actions.reason);

    it.each([
      ['link-ima', trBaglanti.actions.ima.open],
      ['link-pattern', trBaglanti.actions.pattern.open],
      ['link-expert', trBaglanti.actions.expert.open],
    ])('%s: focus goes to the reason field when the form opens', async (testId, open) => {
      const { user } = setup();
      await user.click(await openButton(open));
      expect(reasonOf(testId)).toHaveFocus();
    });

    it('a missing reason shows an alert, focuses it and the link focuses the field', async () => {
      const { user } = setup();
      await user.click(await openButton(trBaglanti.actions.expert.open));
      const box = section('link-expert');
      await user.click(within(box).getByRole('button', { name: trBaglanti.actions.expert.submit }));
      const alert = await within(box).findByRole('alert');
      expect(alert).toHaveTextContent(trBaglanti.actions.summaryTitle);
      // The message is one item of the summary; the field points to it and is invalid.
      expect(within(alert).getAllByText(trBaglanti.actions.reasonRequired)).toHaveLength(1);
      expect(alert.parentElement).toHaveFocus();
      expect(reasonOf('link-expert')).toHaveAttribute('aria-invalid', 'true');
      expect(reasonOf('link-expert')).toHaveAccessibleDescription(
        new RegExp(trBaglanti.actions.reasonRequired),
      );
      await user.click(
        within(alert).getByRole('link', { name: trBaglanti.actions.reasonRequired }),
      );
      expect(reasonOf('link-expert')).toHaveFocus();
    });

    it('moves focus to the error of a refused send and keeps the reason', async () => {
      fake.post('/api/v1/reviews/{id}/ima', problem(409, 'cakisma'));
      const { user } = setup();
      await user.click(await openButton(trBaglanti.actions.ima.open));
      const box = section('link-ima');
      fireEvent.change(reasonOf('link-ima'), { target: { value: 'Gerekçem' } });
      await user.click(within(box).getByRole('button', { name: trBaglanti.actions.ima.submit }));
      const error = await within(box).findByTestId('link-ima-error');
      expect(error).toHaveAttribute('role', 'alert');
      expect(error.parentElement).toHaveFocus();
      expect(reasonOf('link-ima')).toHaveValue('Gerekçem');
    });

    it('moves focus to the heading of the card after a success', async () => {
      fake.post(
        '/api/v1/reviews/{id}/ima',
        ok(
          {
            id: '00000000-0000-4000-8000-0000000000aa',
            review_id: 1,
            type: 'ima',
            status: 'onayli',
          },
          201,
        ),
      );
      const { user } = setup();
      await user.click(await openButton(trBaglanti.actions.ima.open));
      const box = section('link-ima');
      fireEvent.change(reasonOf('link-ima'), { target: { value: 'Dolaylı gönderme' } });
      await user.click(within(box).getByRole('button', { name: trBaglanti.actions.ima.submit }));
      await within(box).findByTestId('link-ima-done');
      await waitFor(() =>
        expect(
          within(box).getByRole('heading', { level: 4, name: trBaglanti.actions.ima.heading }),
        ).toHaveFocus(),
      );
    });

    it('gives focus back to the opening button after "Vazgeç"', async () => {
      const { user } = setup();
      await user.click(await openButton(trBaglanti.actions.pattern.open));
      const box = section('link-pattern');
      await user.click(within(box).getByRole('button', { name: trBaglanti.actions.cancel }));
      expect(
        within(section('link-pattern')).getByRole('button', {
          name: trBaglanti.actions.pattern.open,
        }),
      ).toHaveFocus();
    });

    it('has no axe violation with the forms open, the alerts shown and the fields tied to them', async () => {
      const { container, user } = setup();
      await screen.findByTestId('link-actions');
      for (const open of [
        trBaglanti.actions.ima.open,
        trBaglanti.actions.pattern.open,
        trBaglanti.actions.expert.open,
      ]) {
        await user.click(screen.getByRole('button', { name: open }));
      }
      for (const submit of [
        trBaglanti.actions.ima.submit,
        trBaglanti.actions.pattern.submit,
        trBaglanti.actions.expert.submit,
      ]) {
        await user.click(screen.getByRole('button', { name: submit }));
      }
      await screen.findAllByText(trBaglanti.actions.reasonRequired);
      expect(await violations(container)).toEqual([]);
    });

    it('can be used with the keyboard alone: Tab from the reason reaches the send and cancel buttons', async () => {
      const { user } = setup();
      await user.click(await openButton(trBaglanti.actions.expert.open));
      const box = section('link-expert');
      expect(reasonOf('link-expert')).toHaveFocus();
      await user.keyboard('Uzman görüşü');
      await user.tab();
      expect(
        within(box).getByRole('button', { name: trBaglanti.actions.expert.submit }),
      ).toHaveFocus();
      await user.tab();
      expect(within(box).getByRole('button', { name: trBaglanti.actions.cancel })).toHaveFocus();
      await user.keyboard('{Enter}');
      expect(
        within(section('link-expert')).getByRole('button', {
          name: trBaglanti.actions.expert.open,
        }),
      ).toHaveFocus();
    });
  });

  describe('a re-validation record', () => {
    it('is marked "Yeniden doğrulama" with a note, and the choices are worded for it', async () => {
      const { user } = setup({ detail: revalidationDetail() });
      expect(await screen.findByTestId('revalidation-badge')).toHaveTextContent(
        trBaglanti.revalidation.badge,
      );
      expect(screen.getByTestId('revalidation-note')).toHaveTextContent(
        trBaglanti.revalidation.note,
      );
      const group = screen.getByRole('radiogroup', { name: tr.review.decisionLegend });
      expect(
        within(group)
          .getAllByRole('radio')
          .map((radio) => radio.closest('label')?.textContent),
      ).toEqual([trBaglanti.revalidation.approve, trBaglanti.revalidation.reject]);
      expect(screen.queryByRole('radio', { name: tr.review.approve })).not.toBeInTheDocument();
      expect(screen.queryByRole('radio', { name: tr.review.reject })).not.toBeInTheDocument();
      expect(user).toBeDefined();
    });

    it('hides the target, span and type edit, and the ima and pattern actions; "Uzmana gönder" stays', async () => {
      setup({ detail: revalidationDetail() });
      await screen.findByTestId('revalidation-badge');
      await screen.findByTestId('link-actions');
      expect(screen.queryByTestId('link-edit')).not.toBeInTheDocument();
      expect(screen.queryByTestId('link-ima')).not.toBeInTheDocument();
      expect(screen.queryByTestId('link-pattern')).not.toBeInTheDocument();
      expect(screen.getByTestId('link-expert')).toBeInTheDocument();
    });

    it('"Hâlâ geçerli" is an approval with the same endpoint and body (no edit)', async () => {
      const { user } = setup({ detail: revalidationDetail() });
      await user.click(await screen.findByRole('radio', { name: trBaglanti.revalidation.approve }));
      fireEvent.change(screen.getByLabelText(tr.review.reason), {
        target: { value: 'Hâlâ doğru' },
      });
      await user.click(screen.getByRole('button', { name: tr.review.submit }));
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      const call = decisionCalls()[0]!;
      expect(call.params.id).toBe('1');
      expect(call.headers.get('If-Match')).toBe('"501"');
      expect(call.json).toEqual({ karar: 'onaylandi', duzenlenen: null, gerekce: 'Hâlâ doğru' });
      expect(await screen.findByText(tr.review.decided('onaylandi'))).toBeInTheDocument();
    });

    it('"Geçersiz (kaldır)" is a rejection with the same endpoint and body', async () => {
      const { user } = setup({ detail: revalidationDetail() });
      await user.click(await screen.findByRole('radio', { name: trBaglanti.revalidation.reject }));
      fireEvent.change(screen.getByLabelText(tr.review.reason), {
        target: { value: 'Artık geçerli değil' },
      });
      await user.click(screen.getByRole('button', { name: tr.review.submit }));
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(decisionCalls()[0]!.json).toEqual({
        karar: 'reddedildi',
        duzenlenen: null,
        gerekce: 'Artık geçerli değil',
      });
    });

    it('is not a re-validation unless the target link is approved', async () => {
      setup({
        detail: xrefDetail(1, undefined, undefined, {
          onerilen: REVALIDATION,
          hedef: linkTarget('rn:deneme:p1', 'q:1:2', { status: 'aday' }),
        }),
      });
      await screen.findByRole('radio', { name: tr.review.approve });
      expect(screen.queryByTestId('revalidation-badge')).not.toBeInTheDocument();
      expect(screen.getByTestId('link-edit')).toBeInTheDocument();
      expect(await screen.findByTestId('link-ima')).toBeInTheDocument();
    });

    it('does not mark an ordinary candidate', async () => {
      setup();
      await screen.findByRole('radio', { name: tr.review.approve });
      expect(screen.queryByTestId('revalidation-badge')).not.toBeInTheDocument();
      expect(screen.queryByTestId('revalidation-note')).not.toBeInTheDocument();
    });

    it('marks the row in the list and offers no bulk selection for it (other rows keep theirs)', async () => {
      setup({
        items: [
          xrefItem(1, { onerilen: REVALIDATION }),
          xrefItem(2),
          xrefItem(3, { onerilen: { yeniden_dogrula: false } }),
        ],
        detail: revalidationDetail(),
      });
      const rows = await screen.findAllByRole('link', { name: /00000000-0000-4000-8000/ });
      expect(rows).toHaveLength(3);
      expect(within(rows[0]!).getByTestId('revalidation-badge')).toBeInTheDocument();
      expect(within(rows[1]!).queryByTestId('revalidation-badge')).not.toBeInTheDocument();
      expect(
        screen.queryByRole('checkbox', { name: trBaglanti.selectRow(xrefItem(1).hedef_anahtar) }),
      ).not.toBeInTheDocument();
      expect(
        screen.getByRole('checkbox', { name: trBaglanti.selectRow(xrefItem(2).hedef_anahtar) }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole('checkbox', { name: trBaglanti.selectRow(xrefItem(3).hedef_anahtar) }),
      ).toBeInTheDocument();
    });

    it('has no axe violation', async () => {
      const { container } = setup({ detail: revalidationDetail() });
      await screen.findByTestId('revalidation-badge');
      await screen.findByTestId('link-actions');
      expect(await violations(container)).toEqual([]);
    });
  });
});
