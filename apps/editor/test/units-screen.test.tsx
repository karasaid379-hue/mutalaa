import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { tr } from '@/i18n/tr';
import { trc } from '@/i18n/tr-catalog';
import { ok, problem, useFakeApi } from './fake-api';
import { signedIn, unitDetail } from './fixtures';
import { ARABIC_SAMPLE, tanzilUnit, unitItem, unitPage } from './fixtures-catalog';
import { renderApp } from './render-app';

describe('units screen: list and filters', () => {
  const fake = useFakeApi();

  it('has the title as the h1 and focuses it', async () => {
    signedIn(fake);
    fake.get('/api/v1/units', ok(unitPage([])));
    renderApp(fake, '/birimler');
    const heading = await screen.findByRole('heading', { level: 1, name: tr.nav.units });
    await waitFor(() => expect(heading).toHaveFocus());
    await screen.findByTestId('units-empty');
  });
  const listCalls = () => fake.callsTo('get', '/api/v1/units');

  it('shows the empty state', async () => {
    signedIn(fake);
    fake.get('/api/v1/units', ok(unitPage([])));
    renderApp(fake, '/birimler');
    expect(await screen.findByTestId('units-empty')).toHaveTextContent(trc.units.empty);
    expect(screen.getByText(trc.units.selectPrompt)).toBeInTheDocument();
  });

  it('lists the units without a cursor and without empty filters', async () => {
    signedIn(fake);
    fake.get(
      '/api/v1/units',
      ok(
        unitPage([
          unitItem(),
          unitItem({
            anchor: 'rn:deneme:p2',
            ord: 2,
            metin: 'Deneme paragrafı 2',
            status: 'kullanim_disi',
          }),
          unitItem({ anchor: 'q:1:1', kind: 'ayet', source: 'test-kuran', metin: ARABIC_SAMPLE }),
        ]),
      ),
    );
    renderApp(fake, '/birimler');
    const list = await screen.findByRole('region', { name: trc.units.listLabel });
    expect(await within(list).findAllByRole('listitem')).toHaveLength(3);
    const first = listCalls()[0]!;
    expect(first.search.has('cursor')).toBe(false);
    expect(first.search.has('source')).toBe(false);
    expect(first.search.has('prefix')).toBe(false);
    expect(first.search.has('q')).toBe(false);
    expect(first.search.get('limit')).toBe('50');
    // The state is written out, not only coloured.
    expect(within(list).getByText(trc.unitStatus.kullanim_disi)).toBeInTheDocument();
    expect(within(list).getByText('Deneme paragrafı 2')).toBeInTheDocument();
    // An ayah is shown right to left; the text is as stored.
    const arabic = list.querySelector('[lang="ar"]');
    expect(arabic).toHaveAttribute('dir', 'rtl');
    expect(arabic?.textContent).toBe(ARABIC_SAMPLE);
    expect(within(list).getByText(trc.common.loadedCount(3))).toBeInTheDocument();
  });

  it('sends the filters as source, prefix and q, and keeps them in the address', async () => {
    signedIn(fake);
    fake.get('/api/v1/units', ok(unitPage([unitItem()])));
    const { user, router } = renderApp(fake, '/birimler');
    await screen.findByText('Deneme paragrafı 1');

    await user.type(screen.getByRole('textbox', { name: trc.units.source }), 'test-deneme');
    await user.type(screen.getByRole('textbox', { name: trc.units.prefix }), 'rn:deneme');
    await user.type(screen.getByRole('textbox', { name: trc.units.query }), 'paragraf');
    await user.click(screen.getByRole('button', { name: trc.units.apply }));

    await waitFor(() => expect(listCalls()).toHaveLength(2));
    const second = listCalls()[1]!;
    expect(second.search.get('source')).toBe('test-deneme');
    expect(second.search.get('prefix')).toBe('rn:deneme');
    expect(second.search.get('q')).toBe('paragraf');
    expect(second.search.has('cursor')).toBe(false);
    const search = new URLSearchParams(router.state.location.search);
    expect(search.get('kaynak')).toBe('test-deneme');
    expect(search.get('onek')).toBe('rn:deneme');
    expect(search.get('q')).toBe('paragraf');

    await user.click(screen.getByRole('button', { name: trc.units.clear }));
    await waitFor(() => expect(listCalls()).toHaveLength(3));
    expect(listCalls()[2]!.search.has('source')).toBe(false);
  });

  it('starts from the filters in the address', async () => {
    signedIn(fake);
    fake.get('/api/v1/units', ok(unitPage([])));
    renderApp(fake, '/birimler?kaynak=test-deneme&onek=rn%3A&q=deneme');
    await screen.findByTestId('units-empty');
    const call = listCalls()[0]!;
    expect(call.search.get('source')).toBe('test-deneme');
    expect(call.search.get('prefix')).toBe('rn:');
    expect(call.search.get('q')).toBe('deneme');
    expect(screen.getByRole('textbox', { name: trc.units.source })).toHaveValue('test-deneme');
  });

  it('refuses a query with a NUL character before asking the API', async () => {
    signedIn(fake);
    fake.get('/api/v1/units', ok(unitPage([unitItem()])));
    const { user } = renderApp(fake, '/birimler');
    await screen.findByText('Deneme paragrafı 1');
    fireEvent.change(screen.getByRole('textbox', { name: trc.units.query }), {
      target: { value: 'a\u0000b' },
    });
    await user.click(screen.getByRole('button', { name: trc.units.apply }));
    expect(await screen.findByText(trc.units.queryUnwritable)).toBeInTheDocument();
    expect(listCalls()).toHaveLength(1);
  });

  it('loads the next page with the cursor of the previous one', async () => {
    signedIn(fake);
    fake.get('/api/v1/units', (call) =>
      call.search.get('cursor') === 'imlec-1'
        ? ok(unitPage([unitItem({ anchor: 'rn:deneme:p2', ord: 2 })]))
        : ok(unitPage([unitItem()], 'imlec-1')),
    );
    const { user } = renderApp(fake, '/birimler');
    await screen.findByText('rn:deneme:p1');
    await user.click(screen.getByRole('button', { name: trc.common.loadMore }));
    expect(await screen.findByText('rn:deneme:p2')).toBeInTheDocument();
    expect(listCalls()[1]!.search.get('cursor')).toBe('imlec-1');
    expect(screen.getByText('rn:deneme:p1')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: trc.common.loadMore })).not.toBeInTheDocument();
  });

  it('shows a list error with its code and retries', async () => {
    signedIn(fake);
    let calls = 0;
    fake.get('/api/v1/units', () => {
      calls += 1;
      return calls === 1 ? problem(404, 'bulunamadi') : ok(unitPage([unitItem()]));
    });
    const { user } = renderApp(fake, '/birimler?kaynak=yok-boyle');
    expect(await screen.findByText(trc.units.loadFailed)).toBeInTheDocument();
    expect(screen.getByText(tr.problem.codes.bulunamadi)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: tr.ui.retry }));
    expect(await screen.findByText('Deneme paragrafı 1')).toBeInTheDocument();
  });

  it('opens a unit from the list and keeps the filters', async () => {
    signedIn(fake);
    fake.get('/api/v1/units', ok(unitPage([unitItem()])));
    fake.get('/api/v1/units/{anchor}', ok(unitDetail()));
    const { user, router } = renderApp(fake, '/birimler?kaynak=test-deneme');
    await user.click(await screen.findByRole('link', { name: /rn:deneme:p1/ }));
    expect(
      await screen.findByRole('heading', { level: 2, name: 'rn:deneme:p1' }),
    ).toBeInTheDocument();
    const search = new URLSearchParams(router.state.location.search);
    expect(search.get('birim')).toBe('rn:deneme:p1');
    expect(search.get('kaynak')).toBe('test-deneme');
  });
});

describe('units screen: anchor pre-check', () => {
  const fake = useFakeApi();
  const detailCalls = () => fake.callsTo('get', '/api/v1/units/{anchor}');

  // No detail handler is registered: a request would be answered with 501 and fail the test.
  it.each([
    ['q:999:1', 'SURE_ARALIGI'],
    ['rn:sözler:p1', 'BICIM'],
    ['q:2:255:7-3', 'TERS_ARALIK'],
    ['q:2:255-255', 'KANONIK_DEGIL'],
  ] as const)('does not call the API for %s and shows %s', async (anchor, code) => {
    signedIn(fake);
    fake.get('/api/v1/units', ok(unitPage([])));
    renderApp(fake, `/birimler?birim=${encodeURIComponent(anchor)}`);
    const box = await screen.findByTestId('anchor-invalid');
    expect(box).toHaveTextContent(trc.units.anchorInvalidTitle);
    expect(box).toHaveTextContent(trc.units.anchorErrorCode(code));
    expect(box).toHaveTextContent(trc.units.anchorErrors[code]);
    expect(box).toHaveTextContent(anchor);
    expect(detailCalls()).toHaveLength(0);
  });

  it.each([
    'q:2:255:3',
    'q:2:255:3-7',
    'q:2:255-257',
    'rn:deneme:p1:s2',
    'rn:deneme:p1@0-5',
    'konu:deneme',
  ])('does not call the API for %s, which is not a unit', async (anchor) => {
    signedIn(fake);
    fake.get('/api/v1/units', ok(unitPage([])));
    renderApp(fake, `/birimler?birim=${encodeURIComponent(anchor)}`);
    const box = await screen.findByTestId('anchor-invalid');
    expect(box).toHaveTextContent(trc.units.anchorNotUnit);
    expect(detailCalls()).toHaveLength(0);
  });

  it('checks an anchor typed into "Çapa ile aç" and sends nothing when it is invalid', async () => {
    signedIn(fake);
    fake.get('/api/v1/units', ok(unitPage([])));
    const { user, router } = renderApp(fake, '/birimler');
    await screen.findByTestId('units-empty');
    await user.type(screen.getByRole('textbox', { name: trc.units.openAnchor }), 'Q:2:255');
    await user.click(screen.getByRole('button', { name: trc.units.open }));
    const box = await screen.findByTestId('anchor-invalid');
    expect(box).toHaveTextContent(trc.units.anchorErrorCode('BICIM'));
    expect(new URLSearchParams(router.state.location.search).get('birim')).toBe('Q:2:255');
    expect(detailCalls()).toHaveLength(0);
  });

  it('sends a valid anchor once-encoded in the path and as its raw value to the handler', async () => {
    signedIn(fake);
    fake.get('/api/v1/units', ok(unitPage([])));
    fake.get('/api/v1/units/{anchor}', ok(unitDetail()));
    const { user } = renderApp(fake, '/birimler');
    await screen.findByTestId('units-empty');
    await user.type(screen.getByRole('textbox', { name: trc.units.openAnchor }), 'rn:deneme:p1');
    await user.click(screen.getByRole('button', { name: trc.units.open }));
    await screen.findByRole('heading', { level: 2, name: 'rn:deneme:p1' });
    const call = detailCalls()[0]!;
    expect(call.params.anchor).toBe('rn:deneme:p1');
    // Encoded exactly once: ':' is %3A, and there is no %25 (an encoded percent sign).
    expect(call.path).toBe('/api/v1/units/rn%3Adeneme%3Ap1');
    expect(call.path).not.toContain('%25');
  });

  it('shows the API answer when a well-formed anchor is not found', async () => {
    signedIn(fake);
    fake.get('/api/v1/units', ok(unitPage([])));
    fake.get('/api/v1/units/{anchor}', problem(404, 'bulunamadi'));
    renderApp(fake, '/birimler?birim=rn%3Ayok%3Ap1');
    expect(await screen.findByText(trc.units.detailFailed)).toBeInTheDocument();
    expect(screen.getByText(tr.problem.codes.bulunamadi)).toBeInTheDocument();
  });

  it('shows a 400 capa-gecersiz of the server with its capa_hata_kodu', async () => {
    signedIn(fake);
    fake.get('/api/v1/units', ok(unitPage([])));
    fake.get(
      '/api/v1/units/{anchor}',
      problem(400, 'capa-gecersiz', { capa_hata_kodu: 'SURE_ARALIGI' }),
    );
    renderApp(fake, '/birimler?birim=rn%3Adeneme%3Ap1');
    expect(await screen.findByText(tr.problem.codes['capa-gecersiz'])).toBeInTheDocument();
    expect(screen.getByText(`${tr.problem.anchorCode}: SURE_ARALIGI`)).toBeInTheDocument();
  });
});

describe('units screen: detail', () => {
  const fake = useFakeApi();

  it('shows the text, hash, states, marks and sentences as stored', async () => {
    signedIn(fake);
    const metin = '  Deneme 😀 paragrafı  ';
    fake.get('/api/v1/units', ok(unitPage([])));
    fake.get(
      '/api/v1/units/{anchor}',
      ok(
        unitDetail({
          metin,
          content_hash: 'hash-deneme-123',
          metin_durumu: 'incelemede',
          marks: [
            { s: 9, e: 10, t: 'ar' },
            { s: 2, t: 'hasiye', a: 'rn:deneme:hasiye-1:p1' },
            { s: 5, e: 99, t: 'bozuk' },
          ],
          sentences: [
            [0, 8],
            [8, 99],
          ],
          duzeltilebilir: true,
        }),
      ),
    );
    renderApp(fake, '/birimler?birim=rn%3Adeneme%3Ap1');
    const text = await screen.findByTestId('unit-text');
    // The stored text comes back byte for byte (whitespace kept), in spite of the marks laid over it.
    expect(text.textContent).toBe(metin);
    // Offsets are code points: [9, 10) is the emoji, not two UTF-16 units further.
    const mark = text.querySelector('mark');
    expect(mark?.textContent).toBe('😀');
    expect(mark).toHaveAttribute('data-marks', '1');
    expect(text.querySelector('[data-mark-point="2"]')).not.toBeNull();
    expect(text.querySelectorAll('mark')).toHaveLength(1);

    expect(screen.getByText('hash-deneme-123')).toBeInTheDocument();
    expect(screen.getAllByText(tr.labels.textStatus.incelemede).length).toBeGreaterThan(0);

    const marks = screen.getByRole('table', { name: trc.units.marksNote });
    const rows = within(marks).getAllByRole('row').slice(1);
    expect(rows).toHaveLength(3);
    expect(rows[0]).toHaveAttribute('data-mark-valid', 'true');
    expect(within(rows[1]!).getByText(trc.units.markPoint)).toBeInTheDocument();
    expect(within(rows[1]!).getByText('rn:deneme:hasiye-1:p1')).toBeInTheDocument();
    expect(rows[2]).toHaveAttribute('data-mark-valid', 'false');
    expect(within(rows[2]!).getByText(/Geçersiz aralık/)).toBeInTheDocument();

    const sentences = screen
      .getByRole('heading', { name: trc.units.sentences })
      .closest('section')!;
    const sentenceRows = within(sentences).getAllByRole('row').slice(1);
    expect(sentenceRows[0]).toHaveAttribute('data-sentence-valid', 'true');
    expect(sentenceRows[1]).toHaveAttribute('data-sentence-valid', 'false');
  });

  it('says so when there are no marks or sentences', async () => {
    signedIn(fake);
    fake.get('/api/v1/units', ok(unitPage([])));
    fake.get('/api/v1/units/{anchor}', ok(unitDetail()));
    renderApp(fake, '/birimler?birim=rn%3Adeneme%3Ap1');
    expect(await screen.findByText(trc.units.marksNone)).toBeInTheDocument();
    expect(screen.getByText(trc.units.sentencesNone)).toBeInTheDocument();
  });

  it('shows unreadable marks as raw JSON instead of guessing', async () => {
    signedIn(fake);
    fake.get('/api/v1/units', ok(unitPage([])));
    fake.get('/api/v1/units/{anchor}', ok(unitDetail({ marks: { bozuk: true } })));
    renderApp(fake, '/birimler?birim=rn%3Adeneme%3Ap1');
    expect(await screen.findByText(trc.units.marksUnreadable)).toBeInTheDocument();
    expect(screen.getByText(/"bozuk": true/)).toBeInTheDocument();
  });

  it('shows an ayah right to left with the stored letters and no correction button', async () => {
    signedIn(fake);
    fake.get('/api/v1/units', ok(unitPage([])));
    fake.get('/api/v1/units/{anchor}', ok(tanzilUnit()));
    renderApp(fake, '/birimler?birim=q%3A1%3A1');
    const text = await screen.findByTestId('unit-text');
    const arabic = text.querySelector('[lang="ar"]');
    expect(arabic).toHaveAttribute('dir', 'rtl');
    expect(arabic?.textContent).toBe(ARABIC_SAMPLE);
    // The immutable text has no correction button and no form; a note says why.
    expect(screen.queryByRole('button', { name: trc.units.correct })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Açık soru/ })).not.toBeInTheDocument();
    expect(
      screen.queryByRole('textbox', { name: trc.units.correctionText }),
    ).not.toBeInTheDocument();
    expect(screen.getByText(trc.units.immutableNote)).toBeInTheDocument();
  });

  it.each([
    ['duzeltilebilir is false', { duzeltilebilir: false }],
    ['the unit is an ayah', { kind: 'ayet' }],
    ['the source is a Quran text', { kaynak_tur: 'kuran_metni' }],
  ] as const)('has no correction button when %s', async (_name, over) => {
    signedIn(fake);
    fake.get('/api/v1/units', ok(unitPage([])));
    fake.get('/api/v1/units/{anchor}', ok(unitDetail(over)));
    renderApp(fake, '/birimler?birim=rn%3Adeneme%3Ap1');
    await screen.findByTestId('unit-text');
    // Wait for the session too: the button must not appear once the role is known.
    await screen.findByText(tr.labels.role.editor);
    expect(screen.queryByRole('button', { name: trc.units.correct })).not.toBeInTheDocument();
    expect(screen.getByText(trc.units.immutableNote)).toBeInTheDocument();
  });
});

describe('units screen: correction', () => {
  const fake = useFakeApi();
  const posts = () => fake.callsTo('post', '/api/v1/units/{anchor}/corrections');

  function editable(over: Parameters<typeof unitDetail>[0] = {}) {
    fake.get('/api/v1/units', ok(unitPage([])));
    fake.get('/api/v1/units/{anchor}', ok(unitDetail(over)));
  }

  it('is closed with "Açık soru: A20" on a unit with offset data and sends nothing', async () => {
    signedIn(fake);
    editable({ marks: [{ s: 0, e: 3, t: 'ar' }] });
    const { user } = renderApp(fake, '/birimler?birim=rn%3Adeneme%3Ap1');
    const button = await screen.findByRole('button', {
      name: `${trc.units.correct} · ${tr.openQuestion('A20')}`,
    });
    expect(button).toHaveAttribute('data-open-question', 'A20');
    expect(button).toHaveAttribute('aria-disabled', 'true');
    await user.click(button);
    expect(
      screen.queryByRole('textbox', { name: trc.units.correctionText }),
    ).not.toBeInTheDocument();
    expect(posts()).toHaveLength(0);
  });

  it('is closed on a unit with sentence ranges as well', async () => {
    signedIn(fake);
    editable({ sentences: [[0, 5]] });
    renderApp(fake, '/birimler?birim=rn%3Adeneme%3Ap1');
    expect(await screen.findByRole('button', { name: /Açık soru: A20/ })).toBeInTheDocument();
  });

  it('is hidden for a user without a role', async () => {
    signedIn(fake, []);
    editable();
    renderApp(fake, '/birimler?birim=rn%3Adeneme%3Ap1');
    await screen.findByTestId('unit-text');
    await screen.findByText(tr.session.noRoles);
    expect(screen.queryByRole('button', { name: trc.units.correct })).not.toBeInTheDocument();
  });

  it('asks for a reason and for a changed, writable text before sending', async () => {
    signedIn(fake);
    editable();
    const { user } = renderApp(fake, '/birimler?birim=rn%3Adeneme%3Ap1');
    await user.click(await screen.findByRole('button', { name: trc.units.correct }));
    const text = screen.getByRole('textbox', { name: trc.units.correctionText });
    expect(text).toHaveValue('Deneme paragrafı 1');

    await user.click(screen.getByRole('button', { name: trc.units.correctionSubmit }));
    const summary = await screen.findByRole('alert');
    expect(summary).toHaveTextContent(trc.units.correctionTextUnchanged);
    expect(summary).toHaveTextContent(trc.units.correctionReasonRequired);
    await waitFor(() => expect(summary).toHaveFocus());

    fireEvent.change(text, { target: { value: 'Deneme\u0000 paragrafı' } });
    await user.click(screen.getByRole('button', { name: trc.units.correctionSubmit }));
    expect(await screen.findByText(trc.units.correctionTextUnwritable)).toBeInTheDocument();
    expect(posts()).toHaveLength(0);
  });

  it('sends the text and the reason exactly as typed and reports the new review', async () => {
    signedIn(fake);
    editable();
    fake.post('/api/v1/units/{anchor}/corrections', ok({ id: 41, durum: 'acik' }, 201));
    const { user } = renderApp(fake, '/birimler?birim=rn%3Adeneme%3Ap1');
    await user.click(await screen.findByRole('button', { name: trc.units.correct }));
    const text = screen.getByRole('textbox', { name: trc.units.correctionText });
    const reason = screen.getByRole('textbox', { name: trc.units.correctionReason });
    fireEvent.change(text, { target: { value: '  Deneme paragrafı 1 düzeltilmiş \n' } });
    fireEvent.change(reason, { target: { value: ' Deneme gerekçe  ' } });
    await user.click(screen.getByRole('button', { name: trc.units.correctionSubmit }));

    expect(await screen.findByTestId('correction-done')).toHaveTextContent(
      trc.units.correctionDone(41),
    );
    expect(posts()).toHaveLength(1);
    const call = posts()[0]!;
    expect(call.params.anchor).toBe('rn:deneme:p1');
    expect(call.json).toEqual({
      metin: '  Deneme paragrafı 1 düzeltilmiş \n',
      gerekce: ' Deneme gerekçe  ',
    });
    // The form closes; the button is back and has the focus.
    expect(screen.getByRole('button', { name: trc.units.correct })).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByRole('button', { name: trc.units.correct })).toHaveFocus(),
    );
    expect(screen.getByRole('status')).toHaveTextContent(trc.units.correctionDone(41));
  });

  it('keeps the button in the DOM, toggles aria-expanded and moves the focus into the form and back', async () => {
    signedIn(fake);
    editable();
    const { user } = renderApp(fake, '/birimler?birim=rn%3Adeneme%3Ap1');
    const button = await screen.findByRole('button', { name: trc.units.correct });
    expect(button).toHaveAttribute('aria-expanded', 'false');
    await user.click(button);
    expect(screen.getByRole('button', { name: trc.units.correct })).toBe(button);
    expect(button).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByRole('textbox', { name: trc.units.correctionText })).toHaveFocus();
    await user.click(screen.getByRole('button', { name: trc.units.correctionCancel }));
    expect(button).toHaveAttribute('aria-expanded', 'false');
    expect(button).toHaveFocus();
  });

  it('ties the form messages to their fields', async () => {
    signedIn(fake);
    editable();
    const { user } = renderApp(fake, '/birimler?birim=rn%3Adeneme%3Ap1');
    await user.click(await screen.findByRole('button', { name: trc.units.correct }));
    await user.click(screen.getByRole('button', { name: trc.units.correctionSubmit }));
    const reason = screen.getByRole('textbox', { name: trc.units.correctionReason });
    const text = screen.getByRole('textbox', { name: trc.units.correctionText });
    expect(reason).toHaveAttribute('aria-invalid', 'true');
    expect(text).toHaveAttribute('aria-invalid', 'true');
    const message = screen.getByText(trc.units.correctionReasonRequired).closest('li')!;
    expect(reason.getAttribute('aria-describedby')!.split(' ')).toContain(message.id);
    await user.click(screen.getByRole('link', { name: trc.units.correctionReasonRequired }));
    expect(reason).toHaveFocus();
  });

  it('sends with Ctrl+Enter from the reason field', async () => {
    signedIn(fake);
    editable();
    fake.post('/api/v1/units/{anchor}/corrections', ok({ id: 5, durum: 'acik' }, 201));
    const { user } = renderApp(fake, '/birimler?birim=rn%3Adeneme%3Ap1');
    await user.click(await screen.findByRole('button', { name: trc.units.correct }));
    fireEvent.change(screen.getByRole('textbox', { name: trc.units.correctionText }), {
      target: { value: 'Deneme paragrafı 1 b' },
    });
    const reason = screen.getByRole('textbox', { name: trc.units.correctionReason });
    fireEvent.change(reason, { target: { value: 'gerekçe' } });
    reason.focus();
    await user.keyboard('{Control>}{Enter}{/Control}');
    await waitFor(() => expect(posts()).toHaveLength(1));
  });

  it.each([
    [422, 'degistirilemez-metin', {}, tr.problem.contexts.correction['degistirilemez-metin']],
    [409, 'cakisma', {}, tr.problem.contexts.correction.cakisma],
    [404, 'bulunamadi', {}, tr.problem.codes.bulunamadi],
    [400, 'dogrulama', {}, tr.problem.codes.dogrulama],
    [
      422,
      'inceleme-desteklenmiyor',
      { detail: 'Bu birimin ofsetli alanları (marks, sentences) var.' },
      tr.problem.codes['inceleme-desteklenmiyor'],
    ],
  ] as const)(
    'shows %i %s with its own message and keeps the input',
    async (status, kod, extra, message) => {
      signedIn(fake);
      editable();
      fake.post('/api/v1/units/{anchor}/corrections', problem(status, kod, extra));
      const { user } = renderApp(fake, '/birimler?birim=rn%3Adeneme%3Ap1');
      await user.click(await screen.findByRole('button', { name: trc.units.correct }));
      fireEvent.change(screen.getByRole('textbox', { name: trc.units.correctionText }), {
        target: { value: 'Deneme paragrafı 1 değişti' },
      });
      fireEvent.change(screen.getByRole('textbox', { name: trc.units.correctionReason }), {
        target: { value: 'Deneme gerekçe' },
      });
      await user.click(screen.getByRole('button', { name: trc.units.correctionSubmit }));

      const alert = await screen.findByRole('alert');
      expect(alert).toHaveAttribute('data-problem-code', kod);
      expect(within(alert).getByText(message)).toBeInTheDocument();
      await waitFor(() => expect(alert).toHaveFocus());
      expect(screen.getByRole('textbox', { name: trc.units.correctionText })).toHaveValue(
        'Deneme paragrafı 1 değişti',
      );
    },
  );
});
