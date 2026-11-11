import { screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { tr } from '@/i18n/tr';
import { trc } from '@/i18n/tr-catalog';
import { ok, problem, useFakeApi } from './fake-api';
import { signedIn } from './fixtures';
import { source } from './fixtures-catalog';
import { renderApp } from './render-app';

describe('sources screen', () => {
  const fake = useFakeApi();

  it('has the title as the h1 and focuses it', async () => {
    signedIn(fake);
    fake.get('/api/v1/sources', ok([]));
    renderApp(fake, '/kaynaklar');
    const heading = await screen.findByRole('heading', { level: 1, name: tr.nav.sources });
    await waitFor(() => expect(heading).toHaveFocus());
    await screen.findByTestId('sources-empty');
  });

  it('shows the empty state', async () => {
    signedIn(fake);
    fake.get('/api/v1/sources', ok([]));
    renderApp(fake, '/kaynaklar');
    expect(await screen.findByTestId('sources-empty')).toHaveTextContent(trc.sources.empty);
    expect(screen.getByText(trc.sources.selectPrompt)).toBeInTheDocument();
  });

  it('lists the sources with kind label and unit count, and opens one by its address', async () => {
    signedIn(fake);
    fake.get(
      '/api/v1/sources',
      ok([
        source(),
        source({ slug: 'test-baska', baslik: 'Başka kaynak', tur: 'yeni_tur', birim_sayisi: 2 }),
      ]),
    );
    fake.get('/api/v1/sources/{slug}', (call) =>
      ok(source({ slug: call.params.slug ?? '', baslik: `Ayrıntı ${call.params.slug}` })),
    );
    const { user, router } = renderApp(fake, '/kaynaklar');

    const list = await screen.findByRole('region', { name: trc.sources.listLabel });
    expect(await within(list).findAllByRole('listitem')).toHaveLength(2);
    expect(within(list).getByText('Deneme kaynağı')).toBeInTheDocument();
    expect(within(list).getByText(trc.sourceKind.risale)).toBeInTheDocument();
    expect(within(list).getByText(trc.sources.unitCount('1.234'))).toBeInTheDocument();
    // An unknown kind is shown raw.
    expect(within(list).getByText('yeni_tur')).toBeInTheDocument();

    await user.click(within(list).getByRole('link', { name: /Başka kaynak/ }));
    expect(
      await screen.findByRole('heading', { level: 2, name: 'Ayrıntı test-baska' }),
    ).toBeVisible();
    expect(router.state.location.search).toBe('?kaynak=test-baska');
    expect(fake.callsTo('get', '/api/v1/sources/{slug}')[0]?.params.slug).toBe('test-baska');
  });

  it('shows notice_text and the citation as stored inside pre, without trimming', async () => {
    signedIn(fake);
    const record = source();
    fake.get('/api/v1/sources', ok([record]));
    fake.get('/api/v1/sources/{slug}', ok(record));
    renderApp(fake, '/kaynaklar?kaynak=test-deneme');

    const article = await screen.findByRole('article');
    const pres = article.querySelectorAll('pre');
    const texts = Array.from(pres).map((pre) => pre.textContent);
    expect(texts).toContain(record.atif_metni);
    expect(texts).toContain(record.notice_text);
    expect(record.atif_metni.startsWith('  ')).toBe(true);
    expect(record.notice_text?.startsWith('\n')).toBe(true);
  });

  it('shows the fields and the pipeline/sources note, and offers no way to edit', async () => {
    signedIn(fake);
    const record = source();
    fake.get('/api/v1/sources', ok([record]));
    fake.get('/api/v1/sources/{slug}', ok(record));
    renderApp(fake, '/kaynaklar?kaynak=test-deneme');

    const article = await screen.findByRole('article');
    expect(within(article).getByText(trc.sources.recordNote('test-deneme'))).toBeInTheDocument();
    expect(trc.sources.recordNote('test-deneme')).toBe(
      'Kayıt pipeline/sources/test-deneme.toml dosyasındadır.',
    );
    expect(within(article).getByText(record.dosya_sha256 ?? '')).toBeInTheDocument();
    expect(within(article).getByText('1.234')).toBeInTheDocument();
    expect(
      within(article).getByText(trc.sourceKind.risale, { selector: 'dd' }),
    ).toBeInTheDocument();
    expect(
      within(article).getByRole('link', { name: 'https://deneme.test/kaynak' }),
    ).toHaveAttribute('href', 'https://deneme.test/kaynak');
    expect(within(article).queryByRole('textbox')).not.toBeInTheDocument();
    expect(within(article).getByRole('link', { name: trc.sources.showUnits })).toHaveAttribute(
      'href',
      '/birimler?kaynak=test-deneme',
    );
    expect(fake.callsTo('post', '/api/v1/auth/logout')).toHaveLength(0);
  });

  it('does not make a link of an address that is not a web address', async () => {
    signedIn(fake);
    const record = source({ kaynak_url: 'dosya:deneme', atif_url: null, notice_text: null });
    fake.get('/api/v1/sources', ok([record]));
    fake.get('/api/v1/sources/{slug}', ok(record));
    renderApp(fake, '/kaynaklar?kaynak=test-deneme');
    const article = await screen.findByRole('article');
    expect(within(article).getByText('dosya:deneme')).toBeInTheDocument();
    expect(within(article).queryByRole('link', { name: 'dosya:deneme' })).not.toBeInTheDocument();
  });

  it('shows a list error with its code and retries', async () => {
    signedIn(fake);
    let calls = 0;
    fake.get('/api/v1/sources', () => {
      calls += 1;
      return calls === 1 ? problem(500, 'sunucu-hatasi') : ok([source()]);
    });
    const { user } = renderApp(fake, '/kaynaklar');
    expect(await screen.findByText(trc.sources.loadFailed)).toBeInTheDocument();
    expect(screen.getByText(tr.problem.codes['sunucu-hatasi'])).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: tr.ui.retry }));
    expect(await screen.findByText('Deneme kaynağı')).toBeInTheDocument();
  });

  it('shows a detail error (unknown source) without losing the list', async () => {
    signedIn(fake);
    fake.get('/api/v1/sources', ok([source()]));
    fake.get('/api/v1/sources/{slug}', problem(404, 'bulunamadi'));
    renderApp(fake, '/kaynaklar?kaynak=yok-boyle');
    expect(await screen.findByText(trc.sources.detailFailed)).toBeInTheDocument();
    expect(screen.getByText(tr.problem.codes.bulunamadi)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText('Deneme kaynağı')).toBeInTheDocument());
  });
});
