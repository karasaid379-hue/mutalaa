import { focusManager } from '@tanstack/react-query';
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { tr } from '@/i18n/tr';
import type { Problem } from '@/lib/problem';
import { trc } from '@/i18n/tr-catalog';
import { ok, problem, useFakeApi, type FakeApi } from './fake-api';
import { signedIn } from './fixtures';
import {
  RELEASE_GATE_REPORT,
  accepted,
  releaseDetail,
  releaseItem,
  releasePage,
} from './fixtures-catalog';
import { renderApp } from './render-app';

const ADMIN = ['admin'];

/** Preview handler that answers 200 with a report the gate did not reject. */
function previewOk(fake: FakeApi) {
  fake.post(
    '/api/v1/releases/preview',
    ok({
      derleme: 'dev',
      kapi_raporu: {
        ...RELEASE_GATE_REPORT,
        flavor: 'dev',
        rejected: false,
        violations: [],
        violations_omitted: [],
      },
      uyarilar: ['Deneme uyarısı'],
    }),
  );
}

describe('releases screen: list', () => {
  const fake = useFakeApi();

  it('has the title as the h1 and focuses it', async () => {
    signedIn(fake);
    fake.get('/api/v1/releases', ok(releasePage([])));
    renderApp(fake, '/yayinlar');
    const heading = await screen.findByRole('heading', { level: 1, name: tr.nav.releases });
    await waitFor(() => expect(heading).toHaveFocus());
    await screen.findByTestId('releases-empty');
  });
  const listCalls = () => fake.callsTo('get', '/api/v1/releases');

  it('shows the empty state', async () => {
    signedIn(fake);
    fake.get('/api/v1/releases', ok(releasePage([])));
    renderApp(fake, '/yayinlar');
    expect(await screen.findByTestId('releases-empty')).toHaveTextContent(trc.releases.empty);
    expect(screen.getByText(trc.releases.selectPrompt)).toBeInTheDocument();
  });

  it('lists the releases with their states in words and sends the first request without a cursor', async () => {
    signedIn(fake);
    fake.get(
      '/api/v1/releases',
      ok(
        releasePage([
          releaseItem(),
          releaseItem({
            id: 6,
            surum: '2026.10.9',
            derleme: 'dev',
            durum: 'basarisiz',
            talep: 'geri_alma',
          }),
          releaseItem({ id: 5, surum: '2026.10.8', durum: 'yeni_durum' }),
        ]),
      ),
    );
    renderApp(fake, '/yayinlar');
    const list = await screen.findByRole('region', { name: trc.releases.listLabel });
    expect(await within(list).findAllByRole('listitem')).toHaveLength(3);
    const first = listCalls()[0]!;
    expect(first.search.has('cursor')).toBe(false);
    expect(first.search.has('derleme')).toBe(false);
    expect(first.search.get('limit')).toBe('50');
    expect(within(list).getByText(trc.releases.rowTitle(7, '2026.11.1'))).toBeInTheDocument();
    expect(within(list).getByText(trc.releaseStatus.yayinlandi)).toBeInTheDocument();
    expect(within(list).getByText(trc.releaseStatus.basarisiz)).toBeInTheDocument();
    expect(within(list).getByText(trc.request.geri_alma)).toBeInTheDocument();
    // An unknown state is shown raw.
    expect(within(list).getByText('yeni_durum')).toBeInTheDocument();
  });

  it('filters by derleme and loads the next page with the cursor', async () => {
    signedIn(fake);
    fake.get('/api/v1/releases', (call) =>
      call.search.get('cursor') === 'imlec-1'
        ? ok(releasePage([releaseItem({ id: 3, surum: '2026.9.1' })]))
        : ok(releasePage([releaseItem()], 'imlec-1')),
    );
    const { user, router } = renderApp(fake, '/yayinlar');
    await screen.findByText(trc.releases.rowTitle(7, '2026.11.1'));

    await user.click(screen.getByRole('button', { name: trc.common.loadMore }));
    expect(await screen.findByText(trc.releases.rowTitle(3, '2026.9.1'))).toBeInTheDocument();
    expect(listCalls()[1]!.search.get('cursor')).toBe('imlec-1');

    await user.click(screen.getByRole('combobox', { name: trc.releases.filterLabel }));
    await user.click(await screen.findByRole('option', { name: trc.flavor.public }));
    await waitFor(() =>
      expect(new URLSearchParams(router.state.location.search).get('derleme')).toBe('public'),
    );
    await waitFor(() => expect(listCalls().at(-1)!.search.get('derleme')).toBe('public'));
    expect(listCalls().at(-1)!.search.has('cursor')).toBe(false);
  });

  it('shows a list error with its code and retries', async () => {
    signedIn(fake);
    let calls = 0;
    fake.get('/api/v1/releases', () => {
      calls += 1;
      return calls === 1 ? problem(400, 'dogrulama') : ok(releasePage([releaseItem()]));
    });
    const { user } = renderApp(fake, '/yayinlar?derleme=bozuk');
    expect(await screen.findByText(trc.releases.loadFailed)).toBeInTheDocument();
    expect(screen.getByText(tr.problem.codes.dogrulama)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: tr.ui.retry }));
    expect(await screen.findByText(trc.releases.rowTitle(7, '2026.11.1'))).toBeInTheDocument();
  });
});

describe('releases screen: detail', () => {
  const fake = useFakeApi();

  it('shows the gate report, the digests, the manifest and the fields', async () => {
    signedIn(fake);
    fake.get('/api/v1/releases', ok(releasePage([releaseItem()])));
    fake.get(
      '/api/v1/releases/{id}',
      ok(releaseDetail({ paketler: ['deneme-paket'], kaynak_release_id: 3 })),
    );
    renderApp(fake, '/yayinlar?yayin=7');
    const article = await screen.findByRole('article');
    expect(
      within(article).getByRole('heading', {
        level: 2,
        name: trc.releases.rowTitle(7, '2026.11.1'),
      }),
    ).toBeInTheDocument();
    // Gate report table.
    expect(within(article).getByRole('region', { name: trc.gate.heading })).toBeInTheDocument();
    // The package id is in the gate report and in the digest table.
    expect(within(article).getAllByText('deneme-paket', { selector: 'td' })).toHaveLength(2);
    // Digests.
    expect(within(article).getByText('ozet-kaynak-1')).toBeInTheDocument();
    expect(within(article).getByText('ozet-paket-1')).toBeInTheDocument();
    // Manifest as JSON behind a summary.
    expect(within(article).getByText(trc.releases.manifestShow)).toBeInTheDocument();
    expect(article.querySelector('pre')?.textContent).toContain('"surum": "2026.11.1"');
    // Fields.
    expect(within(article).getByText('Deneme yayın notu')).toBeInTheDocument();
    expect(within(article).getByText('deneme-paket', { selector: 'span' })).toBeInTheDocument();
    expect(within(article).getByRole('link', { name: '3' })).toHaveAttribute(
      'href',
      '/yayinlar?yayin=3',
    );
    expect(screen.getByRole('link', { current: true })).toHaveTextContent(
      trc.releases.rowTitle(7, '2026.11.1'),
    );
  });

  it('says when there is no manifest and no gate report yet', async () => {
    signedIn(fake);
    fake.get('/api/v1/releases', ok(releasePage([releaseItem({ durum: 'basarisiz' })])));
    fake.get(
      '/api/v1/releases/{id}',
      ok(releaseDetail({ durum: 'basarisiz', manifest: null, kapi_raporu: {}, ozetler: {} })),
    );
    renderApp(fake, '/yayinlar?yayin=7');
    expect(await screen.findByText(trc.releases.manifestNone)).toBeInTheDocument();
    expect(screen.getByText(trc.gate.none)).toBeInTheDocument();
    expect(screen.getAllByText(trc.releases.digestsNone)).toHaveLength(2);
  });

  it('shows a detail error with its code', async () => {
    signedIn(fake);
    fake.get('/api/v1/releases', ok(releasePage([])));
    fake.get('/api/v1/releases/{id}', problem(404, 'bulunamadi'));
    renderApp(fake, '/yayinlar?yayin=99');
    expect(await screen.findByText(trc.releases.detailFailed)).toBeInTheDocument();
    expect(screen.getByText(tr.problem.codes.bulunamadi)).toBeInTheDocument();
  });

  it('ignores a ?yayin= that is not a number', async () => {
    signedIn(fake);
    fake.get('/api/v1/releases', ok(releasePage([])));
    renderApp(fake, '/yayinlar?yayin=7abc');
    expect(await screen.findByText(trc.releases.selectPrompt)).toBeInTheDocument();
  });
});

describe('releases screen: roles', () => {
  const fake = useFakeApi();

  async function openInternalRelease(roles: string[]) {
    signedIn(fake, roles);
    fake.get('/api/v1/releases', ok(releasePage([releaseItem()])));
    fake.get('/api/v1/releases/{id}', ok(releaseDetail()));
    const view = renderApp(fake, '/yayinlar?yayin=7');
    await screen.findByRole('article');
    // The session has been read when the header shows the role.
    await screen.findByText(
      roles.length > 0 ? tr.labels.role[roles[0] as 'admin' | 'editor'] : tr.session.noRoles,
    );
    return view;
  }

  it.each([[['editor']], [[]]])('hides every release action for roles %j', async (roles) => {
    await openInternalRelease(roles);
    expect(screen.queryByText(trc.releases.newHeading)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: trc.releases.preview })).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: trc.releases.requestOpen }),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: trc.releases.promote })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: trc.releases.rollback })).not.toBeInTheDocument();
    expect(screen.queryByText(trc.releases.adminHeading)).not.toBeInTheDocument();
  });

  it('shows the actions to an admin', async () => {
    await openInternalRelease(ADMIN);
    expect(screen.getByRole('heading', { name: trc.releases.newHeading })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: trc.releases.preview })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: trc.releases.promote })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: trc.releases.rollback })).toBeInTheDocument();
  });

  it.each([
    ['public', 'yayinlandi', false, true],
    ['internal', 'hazirlaniyor', false, false],
    ['internal', 'basarisiz', false, false],
    ['internal', 'geri_cekildi', false, true],
    ['dev', 'yayinlandi', false, true],
    ['internal', 'yayinlandi', true, true],
  ] as const)(
    'offers promote and rollback by the rule: %s %s → promote %s, rollback %s',
    async (derleme, durum, promote, rollback) => {
      signedIn(fake, ADMIN);
      fake.get('/api/v1/releases', ok(releasePage([])));
      fake.get('/api/v1/releases/{id}', ok(releaseDetail({ derleme, durum })));
      renderApp(fake, '/yayinlar?yayin=7');
      await screen.findByRole('article');
      await screen.findByText(tr.labels.role.admin);
      expect(!!screen.queryByRole('button', { name: trc.releases.promote })).toBe(promote);
      expect(!!screen.queryByRole('button', { name: trc.releases.rollback })).toBe(rollback);
    },
  );
});

describe('releases screen: preview, then request', () => {
  const fake = useFakeApi();
  const calls = (template: string) => fake.callsTo('post', template);

  function admin() {
    signedIn(fake, ADMIN);
    fake.get('/api/v1/releases', ok(releasePage([])));
    fake.get('/api/v1/releases/{id}', (call) =>
      ok(releaseDetail({ id: Number(call.params.id), durum: 'hazirlaniyor' })),
    );
  }

  it('keeps the request closed until a preview has run', async () => {
    admin();
    const { user } = renderApp(fake, '/yayinlar');
    const open = await screen.findByRole('button', { name: trc.releases.requestOpen });
    expect(open).toBeDisabled();
    expect(screen.getByText(trc.releases.previewNeeded)).toBeInTheDocument();
    await user.click(open);
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(calls('/api/v1/releases')).toHaveLength(0);
  });

  it('runs the preview first, shows the gate report and the warnings, then opens the request after a confirmation', async () => {
    admin();
    previewOk(fake);
    fake.post('/api/v1/releases', ok(accepted({ id: 8 }), 202));
    const { user, router } = renderApp(fake, '/yayinlar');

    fireEvent.change(await screen.findByRole('textbox', { name: trc.releases.newNotes }), {
      target: { value: ' Deneme not  ' },
    });
    fireEvent.change(screen.getByRole('textbox', { name: trc.releases.newPacks }), {
      target: { value: 'paket-a, paket-b ,, paket-c' },
    });
    await user.click(screen.getByRole('button', { name: trc.releases.preview }));

    const preview = await screen.findByTestId('release-preview');
    expect(within(preview).getByText('Deneme uyarısı')).toBeInTheDocument();
    expect(within(preview).getByRole('region', { name: trc.gate.heading })).toBeInTheDocument();
    expect(calls('/api/v1/releases/preview')).toHaveLength(1);
    expect(calls('/api/v1/releases/preview')[0]!.json).toEqual({
      derleme: 'dev',
      paketler: ['paket-a', 'paket-b', 'paket-c'],
    });
    // Nothing has been requested yet.
    expect(calls('/api/v1/releases')).toHaveLength(0);

    await user.click(screen.getByRole('button', { name: trc.releases.requestOpen }));
    const dialog = await screen.findByRole('alertdialog', {
      name: trc.releases.confirmCreateTitle,
    });
    expect(
      within(dialog).getByText(trc.releases.confirmCreateBody(trc.flavor.dev)),
    ).toBeInTheDocument();
    // Still nothing sent: the dialog asks first.
    expect(calls('/api/v1/releases')).toHaveLength(0);
    await user.click(within(dialog).getByRole('button', { name: trc.releases.confirm }));

    expect(await screen.findByTestId('release-accepted')).toHaveTextContent(
      trc.releases.accepted(8, '2026.11.2', trc.flavor.internal),
    );
    const created = calls('/api/v1/releases');
    expect(created).toHaveLength(1);
    expect(created[0]!.json).toEqual({
      derleme: 'dev',
      paketler: ['paket-a', 'paket-b', 'paket-c'],
      notlar: ' Deneme not  ',
    });

    // The order of the requests: preview, then request.
    const order = fake.calls.filter((call) => call.method === 'POST').map((call) => call.path);
    expect(order).toEqual(['/api/v1/releases/preview', '/api/v1/releases']);
    // The new release opens in the detail.
    await waitFor(() =>
      expect(new URLSearchParams(router.state.location.search).get('yayin')).toBe('8'),
    );
    expect(await screen.findByRole('heading', { level: 2, name: /Yayın 8/ })).toBeInTheDocument();
  });

  it('asks for a new preview when the derleme changes', async () => {
    admin();
    previewOk(fake);
    const { user } = renderApp(fake, '/yayinlar');
    await user.click(await screen.findByRole('button', { name: trc.releases.preview }));
    const open = screen.getByRole('button', { name: trc.releases.requestOpen });
    await waitFor(() => expect(open).toBeEnabled());

    await user.click(screen.getByRole('combobox', { name: trc.releases.newFlavor }));
    await user.click(await screen.findByRole('option', { name: trc.flavor.internal }));
    await waitFor(() => expect(open).toBeDisabled());
    expect(screen.getByText(trc.releases.previewStale)).toBeInTheDocument();
    expect(calls('/api/v1/releases')).toHaveLength(0);
  });

  it('sends nothing when the confirmation is cancelled', async () => {
    admin();
    previewOk(fake);
    const { user } = renderApp(fake, '/yayinlar');
    await user.click(await screen.findByRole('button', { name: trc.releases.preview }));
    const open = screen.getByRole('button', { name: trc.releases.requestOpen });
    await waitFor(() => expect(open).toBeEnabled());
    await user.click(open);
    const dialog = await screen.findByRole('alertdialog');
    await user.click(within(dialog).getByRole('button', { name: trc.releases.cancel }));
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
    expect(calls('/api/v1/releases')).toHaveLength(0);
  });

  it('refuses notes that are too long or carry a NUL before asking', async () => {
    admin();
    previewOk(fake);
    const { user } = renderApp(fake, '/yayinlar');
    await user.click(await screen.findByRole('button', { name: trc.releases.preview }));
    const open = screen.getByRole('button', { name: trc.releases.requestOpen });
    await waitFor(() => expect(open).toBeEnabled());
    fireEvent.change(screen.getByRole('textbox', { name: trc.releases.newNotes }), {
      target: { value: 'a'.repeat(2001) },
    });
    await user.click(open);
    expect(await screen.findByText(trc.releases.notesTooLong(2001, 2000))).toBeInTheDocument();
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    fireEvent.change(screen.getByRole('textbox', { name: trc.releases.newNotes }), {
      target: { value: 'a\u0000b' },
    });
    await user.click(open);
    expect(await screen.findByText(trc.releases.notesUnwritable)).toBeInTheDocument();
    expect(calls('/api/v1/releases')).toHaveLength(0);
  });

  it('moves focus to the error summary when the preview fails', async () => {
    admin();
    fake.post('/api/v1/releases/preview', problem(503, 'depo-erisilemiyor'));
    const { user } = renderApp(fake, '/yayinlar');
    await user.click(await screen.findByRole('button', { name: trc.releases.preview }));
    const alert = await screen.findByRole('alert');
    await waitFor(() => expect(alert).toHaveFocus());
  });
});

describe('releases screen: every error has its own message', () => {
  const fake = useFakeApi();

  function admin() {
    signedIn(fake, ADMIN);
    fake.get('/api/v1/releases', ok(releasePage([])));
    fake.get('/api/v1/releases/{id}', (call) => ok(releaseDetail({ id: Number(call.params.id) })));
  }

  const OPEN = { id: 5, surum: '2026.11.0', derleme: 'dev', durum: 'hazirlaniyor', talep: 'yayin' };

  it.each<[string, number, string, Partial<Problem>, string]>([
    ['503 depo-erisilemiyor', 503, 'depo-erisilemiyor', {}, tr.problem.codes['depo-erisilemiyor']],
    [
      '422 onceki-yayin-bozuk',
      422,
      'onceki-yayin-bozuk',
      {},
      tr.problem.codes['onceki-yayin-bozuk'],
    ],
    ['409 cakisma', 409, 'cakisma', {}, tr.problem.contexts.release.cakisma],
    [
      '422 kalite-kapisi',
      422,
      'kalite-kapisi',
      { kapi_raporu: RELEASE_GATE_REPORT },
      tr.problem.codes['kalite-kapisi'],
    ],
    [
      '400 dogrulama',
      400,
      'dogrulama',
      { errors: { derleme: ['Geçersiz derleme türü.'] } },
      tr.problem.codes.dogrulama,
    ],
  ])('preview: %s', async (_name, status, kod, extra, message) => {
    admin();
    fake.post('/api/v1/releases/preview', problem(status, kod, extra));
    const { user } = renderApp(fake, '/yayinlar');
    await user.click(await screen.findByRole('button', { name: trc.releases.preview }));
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveAttribute('data-problem-code', kod);
    expect(within(alert).getByText(message)).toBeInTheDocument();
    // A rejected preview shows the report that came with the answer, and the request stays closed.
    if (kod === 'kalite-kapisi') {
      expect(screen.getByRole('region', { name: trc.gate.heading })).toBeInTheDocument();
      expect(screen.getByText('rn:deneme:p1')).toBeInTheDocument();
      expect(screen.getByText(trc.gate.rejected)).toBeInTheDocument();
    }
    expect(screen.getByRole('button', { name: trc.releases.requestOpen })).toBeDisabled();
  });

  async function request(user: ReturnType<typeof renderApp>['user']) {
    await user.click(await screen.findByRole('button', { name: trc.releases.preview }));
    const open = screen.getByRole('button', { name: trc.releases.requestOpen });
    await waitFor(() => expect(open).toBeEnabled());
    await user.click(open);
    const dialog = await screen.findByRole('alertdialog');
    await user.click(within(dialog).getByRole('button', { name: trc.releases.confirm }));
  }

  it('request: 409 yayin-suruyor names the open row and links to it', async () => {
    admin();
    previewOk(fake);
    fake.post('/api/v1/releases', problem(409, 'yayin-suruyor', { yayin: OPEN }));
    const { user } = renderApp(fake, '/yayinlar');
    await request(user);
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveAttribute('data-problem-code', 'yayin-suruyor');
    expect(
      within(alert).getByText(tr.problem.contexts.release['yayin-suruyor']),
    ).toBeInTheDocument();
    expect(alert).toHaveTextContent(`${tr.problem.openRelease}: 5`);
    const link = within(alert).getByRole('link', { name: trc.releases.openReleaseLink });
    expect(link).toHaveAttribute('href', '/yayinlar?yayin=5');
    await waitFor(() => expect(alert).toHaveFocus());
    await user.click(link);
    expect(await screen.findByRole('heading', { level: 2, name: /Yayın 5/ })).toBeInTheDocument();
  });

  it('request: 409 cakisma', async () => {
    admin();
    previewOk(fake);
    fake.post('/api/v1/releases', problem(409, 'cakisma'));
    const { user } = renderApp(fake, '/yayinlar');
    await request(user);
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveAttribute('data-problem-code', 'cakisma');
    expect(within(alert).getByText(tr.problem.contexts.release.cakisma)).toBeInTheDocument();
    // The preview stays valid: the request can be tried again.
    expect(screen.getByRole('button', { name: trc.releases.requestOpen })).toBeEnabled();
  });

  it('promote: 409 yayin-suruyor and 409 durum-gecisi-gecersiz', async () => {
    signedIn(fake, ADMIN);
    fake.get('/api/v1/releases', ok(releasePage([])));
    fake.get('/api/v1/releases/{id}', ok(releaseDetail()));
    let answer: 'suruyor' | 'gecersiz' = 'suruyor';
    fake.post('/api/v1/releases/{id}/promote', () =>
      answer === 'suruyor'
        ? problem(409, 'yayin-suruyor', { yayin: { ...OPEN, derleme: 'public' } })
        : problem(409, 'durum-gecisi-gecersiz'),
    );
    const { user } = renderApp(fake, '/yayinlar?yayin=7');
    const confirm = async () => {
      await user.click(await screen.findByRole('button', { name: trc.releases.promote }));
      const dialog = await screen.findByRole('alertdialog');
      await user.click(within(dialog).getByRole('button', { name: trc.releases.confirm }));
    };

    await confirm();
    let alert = await screen.findByRole('alert');
    expect(alert).toHaveAttribute('data-problem-code', 'yayin-suruyor');
    expect(within(alert).getByRole('link', { name: trc.releases.openReleaseLink })).toHaveAttribute(
      'href',
      '/yayinlar?yayin=5',
    );

    answer = 'gecersiz';
    await confirm();
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveAttribute(
        'data-problem-code',
        'durum-gecisi-gecersiz',
      ),
    );
    alert = screen.getByRole('alert');
    expect(
      within(alert).getByText(tr.problem.contexts.release['durum-gecisi-gecersiz']),
    ).toBeInTheDocument();
  });

  it('rollback: 409 durum-gecisi-gecersiz', async () => {
    signedIn(fake, ADMIN);
    fake.get('/api/v1/releases', ok(releasePage([])));
    fake.get('/api/v1/releases/{id}', ok(releaseDetail()));
    fake.post('/api/v1/releases/{id}/rollback', problem(409, 'durum-gecisi-gecersiz'));
    const { user } = renderApp(fake, '/yayinlar?yayin=7');
    await user.click(await screen.findByRole('button', { name: trc.releases.rollback }));
    const dialog = await screen.findByRole('alertdialog', {
      name: trc.releases.confirmRollbackTitle,
    });
    await user.click(within(dialog).getByRole('button', { name: trc.releases.confirm }));
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveAttribute('data-problem-code', 'durum-gecisi-gecersiz');
    expect(
      within(alert).getByText(tr.problem.contexts.release['durum-gecisi-gecersiz']),
    ).toBeInTheDocument();
  });

  it('uses a different wording for each of the release answers', () => {
    const texts = [
      tr.problem.codes['kalite-kapisi'],
      tr.problem.contexts.release['yayin-suruyor'],
      tr.problem.codes['depo-erisilemiyor'],
      tr.problem.contexts.release.cakisma,
      tr.problem.contexts.release['durum-gecisi-gecersiz'],
      tr.problem.codes['onceki-yayin-bozuk'],
    ];
    expect(new Set(texts).size).toBe(texts.length);
  });
});

describe('releases screen: promote and rollback', () => {
  const fake = useFakeApi();

  function setup() {
    signedIn(fake, ADMIN);
    fake.get('/api/v1/releases', ok(releasePage([])));
    fake.get('/api/v1/releases/{id}', (call) =>
      Number(call.params.id) === 7
        ? ok(releaseDetail())
        : ok(releaseDetail({ id: Number(call.params.id), durum: 'hazirlaniyor' })),
    );
  }

  it('asks first, sends the note as typed and opens the new release', async () => {
    setup();
    fake.post(
      '/api/v1/releases/{id}/promote',
      ok(accepted({ id: 9, derleme: 'public', talep: 'terfi' }), 202),
    );
    const { user, router } = renderApp(fake, '/yayinlar?yayin=7');
    await user.click(await screen.findByRole('button', { name: trc.releases.promote }));
    const dialog = await screen.findByRole('alertdialog', {
      name: trc.releases.confirmPromoteTitle,
    });
    expect(
      within(dialog).getByText(trc.releases.confirmPromoteBody(7, '2026.11.1')),
    ).toBeInTheDocument();
    expect(fake.callsTo('post', '/api/v1/releases/{id}/promote')).toHaveLength(0);
    fireEvent.change(within(dialog).getByRole('textbox', { name: trc.releases.actionNotes }), {
      target: { value: ' Terfi notu ' },
    });
    await user.click(within(dialog).getByRole('button', { name: trc.releases.confirm }));

    await waitFor(() =>
      expect(new URLSearchParams(router.state.location.search).get('yayin')).toBe('9'),
    );
    const call = fake.callsTo('post', '/api/v1/releases/{id}/promote')[0]!;
    expect(call.params.id).toBe('7');
    expect(call.json).toEqual({ notlar: ' Terfi notu ' });
    expect(await screen.findByRole('heading', { level: 2, name: /Yayın 9/ })).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent(
      trc.releases.accepted(9, '2026.11.2', trc.flavor.public),
    );
  });

  it('sends rollback with an empty note as null', async () => {
    setup();
    fake.post('/api/v1/releases/{id}/rollback', ok(accepted({ id: 10, talep: 'geri_alma' }), 202));
    const { user, router } = renderApp(fake, '/yayinlar?yayin=7');
    await user.click(await screen.findByRole('button', { name: trc.releases.rollback }));
    const dialog = await screen.findByRole('alertdialog');
    await user.click(within(dialog).getByRole('button', { name: trc.releases.confirm }));
    await waitFor(() =>
      expect(new URLSearchParams(router.state.location.search).get('yayin')).toBe('10'),
    );
    const call = fake.callsTo('post', '/api/v1/releases/{id}/rollback')[0]!;
    expect(call.params.id).toBe('7');
    expect(call.json).toEqual({ notlar: null });
  });

  it('does nothing when the dialog is cancelled', async () => {
    setup();
    const { user } = renderApp(fake, '/yayinlar?yayin=7');
    await user.click(await screen.findByRole('button', { name: trc.releases.promote }));
    const dialog = await screen.findByRole('alertdialog');
    await user.click(within(dialog).getByRole('button', { name: trc.releases.cancel }));
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
    expect(fake.callsTo('post', '/api/v1/releases/{id}/promote')).toHaveLength(0);
  });
});

describe('releases screen: polling of a release that is being prepared', () => {
  const fake = useFakeApi();
  const detailCalls = () => fake.callsTo('get', '/api/v1/releases/{id}');
  const listCalls = () => fake.callsTo('get', '/api/v1/releases');

  beforeEach(() => {
    // Only the timers: the clock moves on by itself too, so Testing Library's waits keep working.
    vi.useFakeTimers({
      shouldAdvanceTime: true,
      toFake: ['setTimeout', 'clearTimeout', 'setInterval', 'clearInterval'],
    });
  });

  afterEach(() => {
    focusManager.setFocused(undefined);
    vi.useRealTimers();
  });

  async function tick(ms: number) {
    await vi.advanceTimersByTimeAsync(ms);
  }

  it('reads the release again every 5 seconds and stops once it is no longer being prepared', async () => {
    signedIn(fake);
    let reads = 0;
    fake.get('/api/v1/releases', () =>
      ok(releasePage([releaseItem({ durum: reads >= 3 ? 'yayinlandi' : 'hazirlaniyor' })])),
    );
    fake.get('/api/v1/releases/{id}', () => {
      reads += 1;
      return ok(releaseDetail({ durum: reads >= 3 ? 'yayinlandi' : 'hazirlaniyor' }));
    });
    renderApp(fake, '/yayinlar?yayin=7');
    expect(await screen.findByText(trc.releases.preparing)).toBeInTheDocument();
    expect(screen.getByTestId('release-polling')).toHaveTextContent(trc.releases.autoRefreshOn);
    expect(detailCalls()).toHaveLength(1);

    await tick(4000);
    expect(detailCalls()).toHaveLength(1);
    await tick(1500);
    await waitFor(() => expect(detailCalls()).toHaveLength(2));
    await tick(5000);
    await waitFor(() => expect(detailCalls()).toHaveLength(3));

    // The third answer says yayinlandi: the note and the polling switch are gone, the change is announced.
    await waitFor(() => expect(screen.queryByText(trc.releases.preparing)).not.toBeInTheDocument());
    expect(screen.getByRole('status')).toHaveTextContent(
      trc.releases.statusChanged(trc.releaseStatus.yayinlandi),
    );
    await tick(30_000);
    expect(detailCalls()).toHaveLength(3);
    await waitFor(() => expect(screen.queryByTestId('release-polling')).not.toBeInTheDocument());
    // The list was brought up to date when the state changed.
    expect(listCalls().length).toBeGreaterThanOrEqual(2);
  });

  it('does not poll a release that is not being prepared', async () => {
    signedIn(fake);
    fake.get('/api/v1/releases', ok(releasePage([releaseItem()])));
    fake.get('/api/v1/releases/{id}', ok(releaseDetail()));
    renderApp(fake, '/yayinlar?yayin=7');
    await screen.findByRole('article');
    await tick(30_000);
    expect(detailCalls()).toHaveLength(1);
    expect(listCalls()).toHaveLength(1);
    expect(screen.queryByTestId('release-polling')).not.toBeInTheDocument();
  });

  it('can be stopped and started again', async () => {
    signedIn(fake);
    fake.get('/api/v1/releases', ok(releasePage([])));
    fake.get('/api/v1/releases/{id}', ok(releaseDetail({ durum: 'hazirlaniyor' })));
    const { user } = renderApp(fake, '/yayinlar?yayin=7');
    await screen.findByText(trc.releases.preparing);

    await user.click(screen.getByRole('button', { name: trc.releases.autoRefreshStop }));
    expect(screen.getByTestId('release-polling')).toHaveTextContent(trc.releases.autoRefreshOff);
    await tick(20_000);
    expect(detailCalls()).toHaveLength(1);

    await user.click(screen.getByRole('button', { name: trc.releases.autoRefreshStart }));
    await tick(5500);
    await waitFor(() => expect(detailCalls().length).toBeGreaterThanOrEqual(2));
  });

  it('does not poll while the tab is hidden', async () => {
    signedIn(fake);
    fake.get('/api/v1/releases', ok(releasePage([])));
    fake.get('/api/v1/releases/{id}', ok(releaseDetail({ durum: 'hazirlaniyor' })));
    renderApp(fake, '/yayinlar?yayin=7');
    await screen.findByText(trc.releases.preparing);
    focusManager.setFocused(false);
    await tick(20_000);
    expect(detailCalls()).toHaveLength(1);
    focusManager.setFocused(true);
    await tick(5500);
    await waitFor(() => expect(detailCalls().length).toBeGreaterThanOrEqual(2));
  });

  it('polls the list while a listed release is being prepared', async () => {
    signedIn(fake);
    let reads = 0;
    fake.get('/api/v1/releases', () => {
      reads += 1;
      return ok(releasePage([releaseItem({ durum: reads >= 2 ? 'dogrulandi' : 'hazirlaniyor' })]));
    });
    renderApp(fake, '/yayinlar');
    expect(await screen.findByTestId('release-polling')).toBeInTheDocument();
    await tick(5500);
    await waitFor(() => expect(listCalls()).toHaveLength(2));
    await waitFor(() => expect(screen.queryByTestId('release-polling')).not.toBeInTheDocument());
    await tick(20_000);
    expect(listCalls()).toHaveLength(2);
  });
});
