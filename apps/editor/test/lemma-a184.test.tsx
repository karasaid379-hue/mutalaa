// A18.4 on the lemma queue: the wave badge of the list, the "Kelime düzeltmesi öner" form (createWordFix) and the
// edited new value of a word fix approval ("Düzenle ve onayla", duzenlenen = {new_value}).
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import axe from 'axe-core';
import { describe, expect, it } from 'vitest';
import type { components } from '@/api/schema';
import { tr } from '@/i18n/tr';
import { trLemma } from '@/i18n/tr-lemma';
import { LemmaQueue } from '@/screens/lemma/lemma-queue';
import { checkWordAnchor, checkWordFixValue, isWordFixField } from '@/screens/lemma/word-fix-input';
import { ok, problem, useFakeApi } from './fake-api';
import { page, session } from './fixtures';
import {
  fixDetail,
  fixItem,
  glossDetail,
  glossItem,
  lemmaHandlers,
  lemmaItem,
} from './fixtures-lemma';
import { renderInRouter } from './render-app';

type Item = components['schemas']['ReviewItemDto'];
type Detail = components['schemas']['ReviewDetailDto'];

describe('word fix input checks (pure)', () => {
  it('knows the four fields', () => {
    for (const field of ['root_id', 'lemma_id', 'pos', 'features']) {
      expect(isWordFixField(field)).toBe(true);
    }
    expect(isWordFixField('metin')).toBe(false);
  });

  it.each([
    ['', 'anchorEmpty'],
    ['  ', 'anchorEmpty'],
    ['Q:1:1:1', 'anchorInvalid'],
    ['q:115:1:1', 'anchorInvalid'],
    ['q:2:255:3-3', 'anchorInvalid'],
    ['q:1:1', 'anchorNotWord'],
    ['q:2:255:3-7', 'anchorNotWord'],
    ['q:2:255-257', 'anchorNotWord'],
    ['meal:elmalili:1:1', 'anchorNotWord'],
    ['q:1:1:1', null],
    ['q:2:255:12', null],
  ])('reads the word anchor %j as %s', (text, code) => {
    expect(checkWordAnchor(text)).toBe(code);
  });

  it('checks the value against the field', () => {
    expect(checkWordFixValue('root_id', '')).toBe('valueEmpty');
    expect(checkWordFixValue('root_id', '12')).toBeNull();
    expect(checkWordFixValue('root_id', '0')).toBe('idInvalid');
    expect(checkWordFixValue('lemma_id', '1.5')).toBe('idInvalid');
    expect(checkWordFixValue('lemma_id', '2147483648')).toBe('idInvalid');
    expect(checkWordFixValue('pos', 'N')).toBeNull();
    expect(checkWordFixValue('pos', 'a'.repeat(21))).toBe('posTooLong');
    expect(checkWordFixValue('pos', 'a'.repeat(20))).toBeNull();
    expect(checkWordFixValue('features', '{"a": 1}')).toBeNull();
    expect(checkWordFixValue('features', '[1]')).toBe('featuresNotObject');
    expect(checkWordFixValue('features', 'metin')).toBe('featuresNotObject');
    expect(checkWordFixValue('features', `{"a": "${'x'.repeat(2000)}"}`)).toBe('featuresTooLong');
  });
});

describe('LemmaQueue (A18.4)', () => {
  const fake = useFakeApi();
  const listCalls = () => fake.callsTo('get', '/api/v1/reviews');
  const fixCreateCalls = () => fake.callsTo('post', '/api/v1/word-fixes');
  const decisionCalls = () => fake.callsTo('post', '/api/v1/reviews/{id}/decision');

  function setup(
    opts: {
      glosses?: Item[];
      lemmas?: Item[];
      fixes?: Item[];
      route?: string;
      detail?: Detail;
    } = {},
  ) {
    const glosses = opts.glosses ?? [glossItem(1), glossItem(2)];
    const lemmas = opts.lemmas ?? [lemmaItem(101)];
    const fixes = opts.fixes ?? [fixItem(201)];
    fake.get('/api/v1/reviews', (call) => {
      const table = call.search.get('hedef_tablo');
      return ok(page(table === 'lemma' ? lemmas : table === 'quran_word_fix' ? fixes : glosses));
    });
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

  describe('the wave badge of the list', () => {
    it('shows "Dalga n" on the rows that have a wave, as text, and nothing on the others', async () => {
      setup({
        glosses: [glossItem(1, { dalga: 3 }), glossItem(2, { dalga: null }), glossItem(3)],
      });
      const first = await screen.findByRole('link', { name: /^1001/ });
      expect(within(first).getByTestId('lemma-item-wave')).toHaveTextContent(trLemma.list.wave(3));
      expect(screen.getAllByTestId('lemma-item-wave')).toHaveLength(1);
    });

    it('shows the wave on the lemma status tab too', async () => {
      const { user } = setup({ lemmas: [lemmaItem(101, { dalga: 12 })] });
      await user.click(await screen.findByRole('tab', { name: trLemma.tabs.durum }));
      const link = await screen.findByRole('link', { name: /^2101/ });
      expect(within(link).getByTestId('lemma-item-wave')).toHaveTextContent(trLemma.list.wave(12));
    });

    it('has no axe violation with the wave badges', async () => {
      const { container } = setup({ glosses: [glossItem(1, { dalga: 3 }), glossItem(2)] });
      await screen.findByTestId('lemma-item-wave');
      const result = await axe.run(container, {
        rules: { 'color-contrast': { enabled: false }, 'target-size': { enabled: false } },
      });
      expect(result.violations.map((violation) => violation.id)).toEqual([]);
    });
  });

  describe('Kelime düzeltmesi öner', () => {
    const openForm = async (user: ReturnType<typeof setup>['user']) => {
      await screen.findByRole('link', { name: /^1001/ });
      await user.click(await screen.findByRole('button', { name: trLemma.wordFixCreate.open }));
      return screen.getByTestId('word-fix-create');
    };
    const route = '/?kayit=1';

    it('is on the lemma card, closed until opened', async () => {
      setup({ route, detail: glossDetail(1) });
      const section = await screen.findByTestId('word-fix-create');
      expect(
        within(section).getByRole('heading', { level: 3, name: trLemma.wordFixCreate.heading }),
      ).toBeInTheDocument();
      expect(
        within(section).queryByLabelText(trLemma.wordFixCreate.anchor),
      ).not.toBeInTheDocument();
      expect(fixCreateCalls()).toHaveLength(0);
    });

    it('sends {anchor, field, new_value, reason} and says which review record was opened', async () => {
      fake.post('/api/v1/word-fixes', ok({ id: 'fix-1', review_id: 301, durum: 'aday' }, 201));
      const { user } = setup({ route, detail: glossDetail(1) });
      const section = await openForm(user);
      fireEvent.change(within(section).getByLabelText(trLemma.wordFixCreate.anchor), {
        target: { value: 'q:1:1:3' },
      });
      await user.click(within(section).getByRole('radio', { name: 'Lemma' }));
      fireEvent.change(within(section).getByLabelText(trLemma.wordFixCreate.value), {
        target: { value: '1002' },
      });
      fireEvent.change(within(section).getByLabelText(trLemma.wordFixCreate.reason), {
        target: { value: 'QAC değeri hatalı' },
      });
      await user.click(within(section).getByRole('button', { name: trLemma.wordFixCreate.submit }));
      await waitFor(() => expect(fixCreateCalls()).toHaveLength(1));
      expect(fixCreateCalls()[0]!.json).toEqual({
        anchor: 'q:1:1:3',
        field: 'lemma_id',
        new_value: '1002',
        reason: 'QAC değeri hatalı',
      });
      expect(await screen.findByTestId('word-fix-created')).toHaveTextContent(
        trLemma.wordFixCreate.done(301),
      );
      // The correction queue is read again.
      await waitFor(() => expect(listCalls().length).toBeGreaterThan(1));
    });

    it('checks the anchor, the value and the reason before it sends anything', async () => {
      const { user } = setup({ route, detail: glossDetail(1) });
      const section = await openForm(user);
      await user.click(within(section).getByRole('button', { name: trLemma.wordFixCreate.submit }));
      const summary = await screen.findByTestId('word-fix-summary');
      expect(summary).toHaveTextContent(trLemma.wordFixCreate.problems.anchorEmpty);
      expect(summary).toHaveTextContent(trLemma.wordFixCreate.problems.valueEmpty);
      expect(summary).toHaveTextContent(trLemma.wordFixCreate.reasonRequired);
      expect(fixCreateCalls()).toHaveLength(0);
      fireEvent.change(within(section).getByLabelText(trLemma.wordFixCreate.anchor), {
        target: { value: 'q:1:1' },
      });
      fireEvent.change(within(section).getByLabelText(trLemma.wordFixCreate.value), {
        target: { value: 'x' },
      });
      await user.click(within(section).getByRole('button', { name: trLemma.wordFixCreate.submit }));
      expect(await screen.findByTestId('word-fix-summary')).toHaveTextContent(
        trLemma.wordFixCreate.problems.anchorNotWord,
      );
      expect(screen.getByTestId('word-fix-summary')).toHaveTextContent(
        trLemma.wordFixCreate.problems.idInvalid,
      );
      expect(fixCreateCalls()).toHaveLength(0);
    });

    it('shows a 400 and a 409 in Turkish and keeps the typed input', async () => {
      const { user } = setup({ route, detail: glossDetail(1) });
      const section = await openForm(user);
      fireEvent.change(within(section).getByLabelText(trLemma.wordFixCreate.anchor), {
        target: { value: 'q:1:1:3' },
      });
      fireEvent.change(within(section).getByLabelText(trLemma.wordFixCreate.value), {
        target: { value: '999' },
      });
      fireEvent.change(within(section).getByLabelText(trLemma.wordFixCreate.reason), {
        target: { value: 'Gerekçem' },
      });
      fake.post(
        '/api/v1/word-fixes',
        problem(400, 'dogrulama', { detail: 'new_value: 999 kimlikli kok yok.' }),
      );
      await user.click(within(section).getByRole('button', { name: trLemma.wordFixCreate.submit }));
      expect(await screen.findByText(tr.problem.contexts.wordFix.dogrulama)).toBeInTheDocument();
      expect(
        screen.getByText(`${tr.problem.detail}: new_value: 999 kimlikli kok yok.`),
      ).toBeInTheDocument();
      fake.post('/api/v1/word-fixes', problem(409, 'cakisma'));
      await user.click(within(section).getByRole('button', { name: trLemma.wordFixCreate.submit }));
      expect(await screen.findByText(tr.problem.contexts.wordFix.cakisma)).toBeInTheDocument();
      expect(within(section).getByLabelText(trLemma.wordFixCreate.anchor)).toHaveValue('q:1:1:3');
      expect(within(section).getByLabelText(trLemma.wordFixCreate.value)).toHaveValue('999');
      expect(within(section).getByLabelText(trLemma.wordFixCreate.reason)).toHaveValue('Gerekçem');
    });

    it('shows a 404 (no such word) in Turkish', async () => {
      const { user } = setup({ route, detail: glossDetail(1) });
      const section = await openForm(user);
      fireEvent.change(within(section).getByLabelText(trLemma.wordFixCreate.anchor), {
        target: { value: 'q:1:1:9' },
      });
      fireEvent.change(within(section).getByLabelText(trLemma.wordFixCreate.value), {
        target: { value: '5' },
      });
      fireEvent.change(within(section).getByLabelText(trLemma.wordFixCreate.reason), {
        target: { value: 'Gerekçem' },
      });
      fake.post('/api/v1/word-fixes', problem(404, 'bulunamadi'));
      await user.click(within(section).getByRole('button', { name: trLemma.wordFixCreate.submit }));
      expect(await screen.findByText(tr.problem.contexts.wordFix.bulunamadi)).toBeInTheDocument();
    });

    it('has no axe violation with the form open and its errors shown', async () => {
      const { user, container } = setup({ route, detail: glossDetail(1) });
      const section = await openForm(user);
      await user.click(within(section).getByRole('button', { name: trLemma.wordFixCreate.submit }));
      await screen.findByTestId('word-fix-summary');
      const result = await axe.run(container, {
        rules: { 'color-contrast': { enabled: false }, 'target-size': { enabled: false } },
      });
      expect(result.violations.map((violation) => violation.id)).toEqual([]);
    });
  });

  describe('Düzenle ve onayla on a word fix', () => {
    const route = '/?kayit=201';

    it('fills the field with the proposal and sends no edit when it is unchanged', async () => {
      const { user } = setup({ route, detail: fixDetail(201) });
      const edit = await screen.findByTestId('fix-edit');
      expect(within(edit).getByLabelText(trLemma.fix.edit.label)).toHaveValue(
        fixDetail(201).hedef!.new_value,
      );
      await user.click(await screen.findByRole('radio', { name: tr.review.approve }));
      fireEvent.change(screen.getByLabelText(tr.review.reason), { target: { value: 'Uygun' } });
      await user.click(screen.getByRole('button', { name: tr.review.submit }));
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(decisionCalls()[0]!.json).toEqual({
        karar: 'onaylandi',
        duzenlenen: null,
        gerekce: 'Uygun',
      });
    });

    it('sends the edited new value as duzenlenen = {new_value}', async () => {
      const { user } = setup({ route, detail: fixDetail(201) });
      fireEvent.change(await screen.findByLabelText(trLemma.fix.edit.label), {
        target: { value: '1003' },
      });
      await user.click(await screen.findByRole('radio', { name: tr.review.approve }));
      fireEvent.change(screen.getByLabelText(tr.review.reason), { target: { value: 'Düzelttim' } });
      await user.click(screen.getByRole('button', { name: tr.review.submit }));
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      const call = decisionCalls()[0]!;
      expect(call.headers.get('If-Match')).toBe('"701"');
      expect(call.json).toEqual({
        karar: 'onaylandi',
        duzenlenen: { new_value: '1003' },
        gerekce: 'Düzelttim',
      });
    });

    it('blocks an edited value that does not fit the field and sends nothing', async () => {
      const { user } = setup({ route, detail: fixDetail(201) });
      fireEvent.change(await screen.findByLabelText(trLemma.fix.edit.label), {
        target: { value: 'abc' },
      });
      await user.click(await screen.findByRole('radio', { name: tr.review.approve }));
      fireEvent.change(screen.getByLabelText(tr.review.reason), { target: { value: 'Uygun' } });
      await user.click(screen.getByRole('button', { name: tr.review.submit }));
      expect(await screen.findByTestId('decision-summary')).toHaveTextContent(
        trLemma.wordFixCreate.problems.idInvalid,
      );
      expect(decisionCalls()).toHaveLength(0);
    });

    it('sends no edit with a rejection', async () => {
      const { user } = setup({ route, detail: fixDetail(201) });
      fireEvent.change(await screen.findByLabelText(trLemma.fix.edit.label), {
        target: { value: '1003' },
      });
      await user.click(await screen.findByRole('radio', { name: tr.review.reject }));
      fireEvent.change(screen.getByLabelText(tr.review.reason), { target: { value: 'Hayır' } });
      await user.click(screen.getByRole('button', { name: tr.review.submit }));
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect((decisionCalls()[0]!.json as { duzenlenen: unknown }).duzenlenen).toBeNull();
    });

    it('uses a text area for features and checks the JSON object', async () => {
      const detail = fixDetail(201, {
        hedef: { ...fixDetail(201).hedef!, field: 'features', new_value: '{"a": 1}' },
        alan: 'features',
      });
      const { user } = setup({ route, detail });
      const field = await screen.findByLabelText(trLemma.fix.edit.label);
      expect(field.tagName).toBe('TEXTAREA');
      fireEvent.change(field, { target: { value: '[1]' } });
      await user.click(await screen.findByRole('radio', { name: tr.review.approve }));
      fireEvent.change(screen.getByLabelText(tr.review.reason), { target: { value: 'Uygun' } });
      await user.click(screen.getByRole('button', { name: tr.review.submit }));
      expect(await screen.findByTestId('decision-summary')).toHaveTextContent(
        trLemma.wordFixCreate.problems.featuresNotObject,
      );
      expect(decisionCalls()).toHaveLength(0);
    });

    it('shows a 400 of the edited value in Turkish with the server detail and keeps the input', async () => {
      const { user } = setup({ route, detail: fixDetail(201) });
      fake.post(
        '/api/v1/reviews/{id}/decision',
        problem(400, 'dogrulama', { detail: 'duzenlenen.new_value: 1003 kimlikli lemma yok.' }),
      );
      fireEvent.change(await screen.findByLabelText(trLemma.fix.edit.label), {
        target: { value: '1003' },
      });
      await user.click(await screen.findByRole('radio', { name: tr.review.approve }));
      fireEvent.change(screen.getByLabelText(tr.review.reason), { target: { value: 'Uygun' } });
      await user.click(screen.getByRole('button', { name: tr.review.submit }));
      expect(await screen.findByText(tr.problem.codes.dogrulama)).toBeInTheDocument();
      expect(
        screen.getByText(`${tr.problem.detail}: duzenlenen.new_value: 1003 kimlikli lemma yok.`),
      ).toBeInTheDocument();
      expect(screen.getByLabelText(trLemma.fix.edit.label)).toHaveValue('1003');
    });
  });
});
