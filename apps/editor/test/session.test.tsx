import { screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { PROTECTED_PATHS, ROUTE_PATHS } from '@/app/routes';
import { tr } from '@/i18n/tr';
import { noContent, ok, problem, useFakeApi } from './fake-api';
import { EDITOR_EMAIL, OTHER_EMAIL, session, signedIn, stats } from './fixtures';
import { renderApp } from './render-app';

const TITLES: Record<string, string> = {
  '/kuyruk/ocr': tr.nav.queueOcr,
  '/kuyruk/lemma': tr.nav.queueLemma,
  '/kuyruk/baglanti': tr.nav.queueBaglanti,
  '/kuyruk/sure-adi': tr.nav.queueSureAdi,
  '/kaynaklar': tr.nav.sources,
  '/birimler': tr.nav.units,
  '/yayinlar': tr.nav.releases,
};

describe('routes', () => {
  it('are eight: login plus three pages plus four queues (BÇ-12)', () => {
    expect(ROUTE_PATHS).toHaveLength(8);
    expect(PROTECTED_PATHS).toHaveLength(7);
    expect(ROUTE_PATHS).toContain('/kuyruk/sure-adi');
  });
});

describe('session redirect', () => {
  const fake = useFakeApi();

  it.each(ROUTE_PATHS)('%s without a session', async (path) => {
    fake.get('/api/v1/auth/me', problem(401, 'oturum-acilamadi'));
    const { router } = renderApp(fake, path);
    if (path === '/giris') {
      expect(
        await screen.findByRole('heading', { level: 1, name: tr.session.loginTitle }),
      ).toBeInTheDocument();
      expect(router.state.location.pathname).toBe('/giris');
      expect(router.state.location.search).toBe('');
      return;
    }
    expect(
      await screen.findByRole('heading', { level: 1, name: tr.session.loginTitle }),
    ).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/giris');
    expect(new URLSearchParams(router.state.location.search).get('sonraki')).toBe(path);
  });

  it.each(PROTECTED_PATHS)('%s with a session shows its title and focuses the h1', async (path) => {
    signedIn(fake);
    renderApp(fake, path);
    const heading = await screen.findByRole('heading', { level: 1, name: TITLES[path] });
    await waitFor(() => expect(heading).toHaveFocus());
  });

  it('keeps the query of the page asked for in ?sonraki=', async () => {
    fake.get('/api/v1/auth/me', problem(401, 'oturum-acilamadi'));
    const { router } = renderApp(fake, '/kuyruk/ocr?kayit=7');
    await screen.findByRole('heading', { level: 1, name: tr.session.loginTitle });
    expect(new URLSearchParams(router.state.location.search).get('sonraki')).toBe(
      '/kuyruk/ocr?kayit=7',
    );
  });

  it('opens the OCR queue at /', async () => {
    signedIn(fake);
    const { router } = renderApp(fake, '/');
    await screen.findByRole('heading', { level: 1, name: tr.nav.queueOcr });
    expect(router.state.location.pathname).toBe('/kuyruk/ocr');
  });

  it('shows a not-found screen inside the shell for an unknown path', async () => {
    signedIn(fake);
    renderApp(fake, '/yok-boyle-bir-sayfa');
    expect(
      await screen.findByRole('heading', { level: 1, name: tr.ui.notFoundTitle }),
    ).toBeInTheDocument();
  });

  it('shows the user, the roles and the queue counts; there is one live region', async () => {
    fake.get('/api/v1/auth/me', ok(session(['admin', 'editor'])));
    fake.get(
      '/api/v1/reviews/stats',
      ok(
        stats([
          ['unit', 'metin', 12],
          ['xref', 'status', 5],
        ]),
      ),
    );
    renderApp(fake, '/kuyruk/ocr');
    expect(await screen.findByText(EDITOR_EMAIL)).toBeInTheDocument();
    expect(
      screen.getByText(`${tr.labels.role.admin}, ${tr.labels.role.editor}`),
    ).toBeInTheDocument();
    const nav = screen.getByRole('navigation', { name: tr.nav.label });
    await waitFor(() => expect(nav).toHaveTextContent(`${tr.nav.queueOcr}12`));
    expect(nav).toHaveTextContent(`${tr.nav.queueBaglanti}5`);
    expect(screen.getAllByRole('status')).toHaveLength(1);
  });
});

describe('403 (a user without a role)', () => {
  const fake = useFakeApi();

  it('goes to the no-permission page, which has no logout button', async () => {
    fake.get('/api/v1/auth/me', problem(403, 'yetki-yok'));
    const { router } = renderApp(fake, '/kuyruk/lemma');
    expect(
      await screen.findByRole('heading', { level: 1, name: tr.session.forbiddenTitle }),
    ).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/yetki-yok');
    expect(screen.queryByRole('button', { name: tr.session.logout })).not.toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
    expect(fake.callsTo('get', '/api/v1/auth/me')).toHaveLength(1);
  });
});

describe('401 in the middle of a page', () => {
  const fake = useFakeApi();

  it('navigates to the login page first and clears the query cache afterwards', async () => {
    let expired = false;
    let release: () => void = () => {};
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    fake.get('/api/v1/auth/me', () => (expired ? problem(401, 'oturum-acilamadi') : ok(session())));
    fake.get('/api/v1/reviews/stats', async () => {
      await gate;
      expired = true;
      return problem(401, 'oturum-acilamadi');
    });
    const { router, queryClient } = renderApp(fake, '/kuyruk/lemma');
    await screen.findByRole('heading', { level: 1, name: tr.nav.queueLemma });

    const seenAtClear: string[] = [];
    const clear = queryClient.clear.bind(queryClient);
    vi.spyOn(queryClient, 'clear').mockImplementation(() => {
      seenAtClear.push(router.state.location.pathname);
      clear();
    });
    release();

    expect(
      await screen.findByRole('heading', { level: 1, name: tr.session.loginTitle }),
    ).toBeInTheDocument();
    await waitFor(() => expect(seenAtClear).toEqual(['/giris']));
    expect(new URLSearchParams(router.state.location.search).get('sonraki')).toBe('/kuyruk/lemma');
    expect(queryClient.getQueryCache().getAll()).toHaveLength(0);
  });
});

describe('logout', () => {
  const fake = useFakeApi();

  it('goes to /giris?cikis=1 without asking me, explains the dev auto login and clears the cache', async () => {
    signedIn(fake);
    fake.post('/api/v1/auth/logout', noContent());
    const { router, queryClient, user } = renderApp(fake, '/kuyruk/ocr');
    await screen.findByText(EDITOR_EMAIL);
    const meCalls = fake.callsTo('get', '/api/v1/auth/me').length;

    await user.click(screen.getByRole('button', { name: tr.session.logout }));

    expect(await screen.findByTestId('logged-out-note')).toHaveTextContent(tr.session.loggedOut);
    expect(screen.getByTestId('logged-out-note')).toHaveTextContent(tr.session.devAutoLoginNote);
    expect(router.state.location.pathname).toBe('/giris');
    expect(router.state.location.search).toBe('?cikis=1');
    expect(fake.callsTo('post', '/api/v1/auth/logout')).toHaveLength(1);
    expect(fake.callsTo('get', '/api/v1/auth/me')).toHaveLength(meCalls);
    await waitFor(() => expect(queryClient.getQueryCache().getAll()).toHaveLength(0));
  });

  it('stays and shows the problem when logout fails', async () => {
    signedIn(fake);
    fake.post('/api/v1/auth/logout', problem(500, 'sunucu-hatasi'));
    const { router, user } = renderApp(fake, '/kuyruk/ocr');
    await screen.findByText(EDITOR_EMAIL);
    await user.click(screen.getByRole('button', { name: tr.session.logout }));
    expect(await screen.findByText(tr.problem.codes['sunucu-hatasi'])).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/kuyruk/ocr');
  });
});

describe('login page', () => {
  const fake = useFakeApi();

  it('sends e-mail and password, then returns to ?sonraki=', async () => {
    let signed = false;
    fake.get('/api/v1/auth/me', () => (signed ? ok(session()) : problem(401, 'oturum-acilamadi')));
    fake.get('/api/v1/reviews/stats', ok(stats()));
    fake.post('/api/v1/auth/login', () => {
      signed = true;
      return ok(session());
    });
    const { router, user } = renderApp(fake, '/giris?sonraki=%2Fbirimler');
    await user.type(await screen.findByLabelText(tr.session.email), OTHER_EMAIL);
    await user.type(screen.getByLabelText(tr.session.password), 'deneme-parolasi-1');
    await user.click(screen.getByRole('button', { name: tr.session.submit }));

    expect(
      await screen.findByRole('heading', { level: 1, name: tr.nav.units }),
    ).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/birimler');
    expect(fake.callsTo('post', '/api/v1/auth/login')[0]?.json).toEqual({
      email: OTHER_EMAIL,
      parola: 'deneme-parolasi-1',
    });
  });

  it('shows the Turkish message for a wrong password and focuses it', async () => {
    fake.get('/api/v1/auth/me', problem(401, 'oturum-acilamadi'));
    fake.post('/api/v1/auth/login', problem(401, 'oturum-acilamadi'));
    const { user } = renderApp(fake, '/giris');
    await user.type(await screen.findByLabelText(tr.session.email), OTHER_EMAIL);
    await user.type(screen.getByLabelText(tr.session.password), 'yanlis');
    await user.click(screen.getByRole('button', { name: tr.session.submit }));
    const alert = await screen.findByText(tr.problem.contexts.login['oturum-acilamadi']);
    expect(alert.closest('[role="alert"]')).toHaveFocus();
  });

  it('skips the form for a live session and ignores an unsafe ?sonraki=', async () => {
    signedIn(fake);
    const { router } = renderApp(fake, '/giris?sonraki=https%3A%2F%2Fevil.example%2F');
    await screen.findByRole('heading', { level: 1, name: tr.nav.queueOcr });
    expect(router.state.location.pathname).toBe('/kuyruk/ocr');
  });

  it('follows a safe local ?sonraki= for a live session', async () => {
    signedIn(fake);
    const { router } = renderApp(fake, '/giris?sonraki=%2Fyayinlar');
    await screen.findByRole('heading', { level: 1, name: tr.nav.releases });
    expect(router.state.location.pathname).toBe('/yayinlar');
  });
});
