// Risale book approval in the editor (A20.8, K-51 madde 11): the book list inside the Risale text source, the
// admin-only "kitabı onayla" button, the confirmation dialog with If-Match, the problem texts and an axe pass.
// Data is synthetic ("Deneme kitap"); there is no Risale text.
import { screen, waitFor, within } from '@testing-library/react';
import axe from 'axe-core';
import { describe, expect, it } from 'vitest';
import { tr } from '@/i18n/tr';
import { trc } from '@/i18n/tr-catalog';
import { formatBookIfMatch } from '@/lib/etag';
import { canApproveBooks } from '@/lib/roles';
import { ok, problem, useFakeApi, type FakeApi } from './fake-api';
import { signedIn } from './fixtures';
import { BOOK_DIGEST, risaleBook, risaleBookDetail, source } from './fixtures-catalog';
import { renderApp } from './render-app';

const TEXT_SOURCE = 'risale-rnk-metin';
const OTHER_DIGEST = 'd'.repeat(64);

function openSource(fake: FakeApi, slug = TEXT_SOURCE) {
  fake.get('/api/v1/sources', ok([source({ slug })]));
  fake.get('/api/v1/sources/{slug}', ok(source({ slug })));
  return renderApp(fake, `/kaynaklar?kaynak=${slug}`);
}

async function violations(container: HTMLElement): Promise<string[]> {
  const result = await axe.run(container, {
    rules: { 'color-contrast': { enabled: false }, 'target-size': { enabled: false } },
  });
  return result.violations.map(
    (violation) =>
      `${violation.id}: ${violation.nodes.map((node) => node.target.join(' ')).join(' | ')}`,
  );
}

async function openDialog(user: ReturnType<typeof renderApp>['user']) {
  await user.click(await screen.findByRole('button', { name: /Kitabı onayla/ }));
  return screen.findByRole('alertdialog');
}

describe('Risale book approval: helpers', () => {
  it('formats the If-Match value as a quoted digest and gates the button by the admin role', () => {
    expect(formatBookIfMatch(BOOK_DIGEST)).toBe(`"${BOOK_DIGEST}"`);
    expect(canApproveBooks(['admin'])).toBe(true);
    expect(canApproveBooks(['editor'])).toBe(false);
    expect(canApproveBooks(null)).toBe(false);
  });
});

describe('Risale books panel', () => {
  const fake = useFakeApi();

  it('lists the books with counts and shows the approve button to an admin', async () => {
    signedIn(fake, ['admin']);
    fake.get(
      '/api/v1/risale/books',
      ok([
        risaleBook(),
        risaleBook({
          slug: 'deneme-osmanlica',
          baslik: 'Deneme Osmanlıca',
          dil: 'ota',
          dogrulandi: false,
          birim_sayisi: 4,
          taslak_sayisi: 0,
          onayli_sayisi: 4,
        }),
      ]),
    );
    openSource(fake);

    const section = await screen.findByRole('region', { name: trc.risale.heading });
    const rows = await within(section).findAllByRole('row');
    expect(rows).toHaveLength(3); // header + two books
    const first = within(rows[1]!);
    expect(first.getByText('Deneme kitap')).toBeInTheDocument();
    expect(first.getByText(trc.risale.language.tr)).toBeInTheDocument();
    expect(first.getByText('deneme-kitap')).toBeInTheDocument();
    expect(first.getByRole('button', { name: /Kitabı onayla.*Deneme kitap/ })).toBeInTheDocument();
    const second = within(rows[2]!);
    expect(second.getByText(trc.risale.language.ota)).toBeInTheDocument();
    expect(second.getByText(trc.risale.noDraft)).toBeInTheDocument();
    expect(second.queryByRole('button')).not.toBeInTheDocument();
    expect(within(section).getAllByRole('columnheader')).toHaveLength(7);
  });

  it('shows the list read-only to an editor, without the action column or button', async () => {
    signedIn(fake, ['editor']);
    fake.get('/api/v1/risale/books', ok([risaleBook()]));
    openSource(fake);

    const section = await screen.findByRole('region', { name: trc.risale.heading });
    await within(section).findByText('Deneme kitap');
    expect(within(section).getByText(trc.risale.adminOnly)).toBeInTheDocument();
    expect(within(section).queryByRole('button')).not.toBeInTheDocument();
    expect(within(section).getAllByRole('columnheader')).toHaveLength(6);
  });

  it('is not shown on a source that is not the Risale text source', async () => {
    signedIn(fake, ['admin']);
    openSource(fake, 'test-deneme');
    await screen.findByRole('article');
    expect(screen.queryByRole('region', { name: trc.risale.heading })).not.toBeInTheDocument();
    expect(fake.callsTo('get', '/api/v1/risale/books')).toHaveLength(0);
  });

  it('shows a list error with its code and retries', async () => {
    signedIn(fake, ['admin']);
    let calls = 0;
    fake.get('/api/v1/risale/books', () => {
      calls += 1;
      return calls === 1 ? problem(500, 'sunucu-hatasi') : ok([risaleBook()]);
    });
    const { user } = openSource(fake);

    expect(await screen.findByText(trc.risale.loadFailed)).toBeInTheDocument();
    expect(screen.getByText(tr.problem.codes['sunucu-hatasi'])).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: tr.ui.retry }));
    expect(await screen.findByText('Deneme kitap')).toBeInTheDocument();
  });

  it('shows the empty state', async () => {
    signedIn(fake, ['admin']);
    fake.get('/api/v1/risale/books', ok([]));
    openSource(fake);
    expect(await screen.findByTestId('risale-empty')).toHaveTextContent(trc.risale.empty);
  });
});

describe('Risale book approval dialog', () => {
  const fake = useFakeApi();

  function setup(detail = risaleBookDetail()) {
    signedIn(fake, ['admin']);
    fake.get('/api/v1/risale/books', ok([risaleBook()]));
    fake.get('/api/v1/risale/books/{kitap}', ok(detail));
    return openSource(fake);
  }

  it('reads the book, shows the draft count and the prerequisites, and has no violations (axe)', async () => {
    const { user } = setup();
    const dialog = await openDialog(user);

    expect(within(dialog).getByText(trc.risale.dialogTitle('Deneme kitap'))).toBeInTheDocument();
    expect(await within(dialog).findByText(trc.risale.dialogBody('7'))).toBeInTheDocument();
    expect(within(dialog).getByText(trc.risale.evidenceOk)).toBeInTheDocument();
    expect(within(dialog).getByText(trc.risale.slugOk)).toBeInTheDocument();
    expect(within(dialog).getByText(BOOK_DIGEST)).toBeInTheDocument();
    expect(fake.callsTo('get', '/api/v1/risale/books/{kitap}')[0]?.params.kitap).toBe(
      'deneme-kitap',
    );
    expect(await violations(document.body)).toEqual([]);
  });

  it('shows missing prerequisites in the dialog before anything is sent', async () => {
    const { user } = setup(
      risaleBookDetail({ gbut_kaniti: false, kanitsiz_birim_sayisi: 2, dogrulandi: false }),
    );
    const dialog = await openDialog(user);

    expect(await within(dialog).findByText(trc.risale.evidenceMissing('2'))).toBeInTheDocument();
    expect(within(dialog).getByText(trc.risale.slugMissing)).toBeInTheDocument();
  });

  it('refuses an empty reason and an unchecked sample reading without sending anything', async () => {
    const { user } = setup();
    const dialog = await openDialog(user);
    await within(dialog).findByText(trc.risale.dialogBody('7'));

    await user.click(within(dialog).getByRole('button', { name: trc.risale.confirm }));

    expect(within(dialog).getByText(trc.risale.reasonRequired)).toBeInTheDocument();
    expect(within(dialog).getByText(trc.risale.sampleRequired)).toBeInTheDocument();
    expect(within(dialog).getByRole('textbox', { name: trc.risale.reasonLabel })).toBeInvalid();
    expect(fake.callsTo('post', '/api/v1/risale/books/{kitap}/approve')).toHaveLength(0);
    expect(await violations(document.body)).toEqual([]);
  });

  it('refuses a reason with an unwritable character and one that is too long', async () => {
    const { user } = setup();
    const dialog = await openDialog(user);
    await within(dialog).findByText(trc.risale.dialogBody('7'));
    const reason = within(dialog).getByRole('textbox', { name: trc.risale.reasonLabel });
    await user.click(within(dialog).getByRole('checkbox', { name: trc.risale.sampleLabel }));

    await user.click(reason);
    await user.paste('a'.repeat(2001));
    await user.click(within(dialog).getByRole('button', { name: trc.risale.confirm }));
    expect(within(dialog).getByText(trc.risale.reasonTooLong(2001, 2000))).toBeInTheDocument();

    expect(fake.callsTo('post', '/api/v1/risale/books/{kitap}/approve')).toHaveLength(0);
  });

  it('sends If-Match with the digest, the reason and the declaration, then closes and shows the result', async () => {
    const { user } = setup();
    fake.post(
      '/api/v1/risale/books/{kitap}/approve',
      ok({
        kitap: 'deneme-kitap',
        review_id: 5,
        onaylanan_birim_sayisi: 7,
        ozet: BOOK_DIGEST,
      }),
    );
    const dialog = await openDialog(user);
    await within(dialog).findByText(trc.risale.dialogBody('7'));

    await user.click(within(dialog).getByRole('checkbox', { name: trc.risale.sampleLabel }));
    await user.type(
      within(dialog).getByRole('textbox', { name: trc.risale.reasonLabel }),
      'Deneme gerekçesi',
    );
    await user.click(within(dialog).getByRole('button', { name: trc.risale.confirm }));

    const result = await screen.findByTestId('risale-approved');
    expect(result).toHaveTextContent(trc.risale.approved('Deneme kitap', '7'));
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
    const [call] = fake.callsTo('post', '/api/v1/risale/books/{kitap}/approve');
    expect(call?.params.kitap).toBe('deneme-kitap');
    expect(call?.headers.get('If-Match')).toBe(`"${BOOK_DIGEST}"`);
    expect(call?.json).toEqual({ gerekce: 'Deneme gerekçesi', ornek_okuma_yapildi: true });
    // The list is read again after the approval.
    await waitFor(() =>
      expect(fake.callsTo('get', '/api/v1/risale/books').length).toBeGreaterThan(1),
    );
  });

  it('lists the missing prerequisites of a 422 on-kosul-eksik answer and keeps the input', async () => {
    const { user } = setup();
    fake.post(
      '/api/v1/risale/books/{kitap}/approve',
      problem(422, 'on-kosul-eksik', { eksikler: ['gbut-kaniti-yok', 'slug-dogrulanmadi'] }),
    );
    const dialog = await openDialog(user);
    await within(dialog).findByText(trc.risale.dialogBody('7'));
    await user.click(within(dialog).getByRole('checkbox', { name: trc.risale.sampleLabel }));
    await user.type(
      within(dialog).getByRole('textbox', { name: trc.risale.reasonLabel }),
      'Deneme gerekçesi',
    );

    await user.click(within(dialog).getByRole('button', { name: trc.risale.confirm }));

    expect(await within(dialog).findByText(tr.problem.codes['on-kosul-eksik'])).toBeInTheDocument();
    expect(within(dialog).getByText(tr.problem.missingHeading)).toBeInTheDocument();
    expect(
      within(dialog).getByText(tr.problem.prerequisites['gbut-kaniti-yok']!),
    ).toBeInTheDocument();
    expect(
      within(dialog).getByText(tr.problem.prerequisites['slug-dogrulanmadi']!),
    ).toBeInTheDocument();
    expect(
      within(dialog).queryByText(tr.problem.prerequisites['ornek-okuma-yok']!),
    ).not.toBeInTheDocument();
    expect(within(dialog).getByRole('textbox', { name: trc.risale.reasonLabel })).toHaveValue(
      'Deneme gerekçesi',
    );
    expect(screen.getByRole('alertdialog')).toBeInTheDocument();
    expect(await violations(document.body)).toEqual([]);
  });

  it('shows the 422 onaylanacak-birim-yok answer', async () => {
    const { user } = setup();
    fake.post('/api/v1/risale/books/{kitap}/approve', problem(422, 'onaylanacak-birim-yok'));
    const dialog = await openDialog(user);
    await within(dialog).findByText(trc.risale.dialogBody('7'));
    await user.click(within(dialog).getByRole('checkbox', { name: trc.risale.sampleLabel }));
    await user.type(
      within(dialog).getByRole('textbox', { name: trc.risale.reasonLabel }),
      'Deneme',
    );

    await user.click(within(dialog).getByRole('button', { name: trc.risale.confirm }));

    expect(
      await within(dialog).findByText(tr.problem.codes['onaylanacak-birim-yok']),
    ).toBeInTheDocument();
  });

  it('reloads the book on 412, keeps the input and sends the new digest on the next try', async () => {
    signedIn(fake, ['admin']);
    fake.get('/api/v1/risale/books', ok([risaleBook()]));
    let reads = 0;
    fake.get('/api/v1/risale/books/{kitap}', () => {
      reads += 1;
      return ok(risaleBookDetail({ ozet: reads === 1 ? BOOK_DIGEST : OTHER_DIGEST }));
    });
    let posts = 0;
    fake.post('/api/v1/risale/books/{kitap}/approve', () => {
      posts += 1;
      return posts === 1
        ? problem(412, 'surum-uyusmazligi')
        : ok({
            kitap: 'deneme-kitap',
            review_id: 6,
            onaylanan_birim_sayisi: 7,
            ozet: OTHER_DIGEST,
          });
    });
    const { user } = openSource(fake);
    const dialog = await openDialog(user);
    await within(dialog).findByText(trc.risale.dialogBody('7'));
    await user.click(within(dialog).getByRole('checkbox', { name: trc.risale.sampleLabel }));
    await user.type(
      within(dialog).getByRole('textbox', { name: trc.risale.reasonLabel }),
      'Deneme gerekçesi',
    );

    await user.click(within(dialog).getByRole('button', { name: trc.risale.confirm }));

    expect(
      await within(dialog).findByText(tr.problem.contexts.risaleBook['surum-uyusmazligi']!),
    ).toBeInTheDocument();
    expect(await within(dialog).findByText(OTHER_DIGEST)).toBeInTheDocument();
    expect(within(dialog).getByRole('textbox', { name: trc.risale.reasonLabel })).toHaveValue(
      'Deneme gerekçesi',
    );
    expect(within(dialog).getByRole('checkbox', { name: trc.risale.sampleLabel })).toBeChecked();

    await user.click(within(dialog).getByRole('button', { name: trc.risale.confirm }));
    await screen.findByTestId('risale-approved');
    const calls = fake.callsTo('post', '/api/v1/risale/books/{kitap}/approve');
    expect(calls.map((call) => call.headers.get('If-Match'))).toEqual([
      `"${BOOK_DIGEST}"`,
      `"${OTHER_DIGEST}"`,
    ]);
  });

  it('shows a detail error and sends nothing when the book cannot be read', async () => {
    signedIn(fake, ['admin']);
    fake.get('/api/v1/risale/books', ok([risaleBook()]));
    fake.get('/api/v1/risale/books/{kitap}', problem(404, 'bulunamadi'));
    const { user } = openSource(fake);
    const dialog = await openDialog(user);

    expect(await within(dialog).findByText(trc.risale.detailFailed)).toBeInTheDocument();
    expect(
      within(dialog).getByText(tr.problem.contexts.risaleBook.bulunamadi!),
    ).toBeInTheDocument();
    expect(within(dialog).getByRole('button', { name: trc.risale.confirm })).toBeDisabled();
    expect(fake.callsTo('post', '/api/v1/risale/books/{kitap}/approve')).toHaveLength(0);
  });

  it('closes with Vazgeç without sending anything', async () => {
    const { user } = setup();
    const dialog = await openDialog(user);
    await within(dialog).findByText(trc.risale.dialogBody('7'));

    await user.click(within(dialog).getByRole('button', { name: trc.risale.cancel }));

    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
    expect(fake.callsTo('post', '/api/v1/risale/books/{kitap}/approve')).toHaveLength(0);
  });
});

describe('Risale books panel: axe', () => {
  const fake = useFakeApi();

  it('the list with the action column has no violations', async () => {
    signedIn(fake, ['admin']);
    fake.get(
      '/api/v1/risale/books',
      ok([
        risaleBook(),
        risaleBook({ slug: 'deneme-iki', baslik: 'Deneme iki', taslak_sayisi: 0 }),
      ]),
    );
    const { container } = openSource(fake);
    await screen.findByRole('button', { name: /Kitabı onayla/ });
    expect(await violations(container)).toEqual([]);
  });
});
