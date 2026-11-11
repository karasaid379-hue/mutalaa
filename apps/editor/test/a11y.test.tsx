// axe-core pass over the whole panel (A15.6): the eight routes with empty data, three details (OCR card, surah
// name card, unit and release detail), the meal queue and its two cards (A16.5: head and follower unit), the decision form while it shows a 412 difference, the error and loading
// states, the login page and the 403 page, the link candidates card in full (evidence, four missing sections,
// closed buttons, decision form) and its 10 percent sample panel with the bulk flag injected on. Zero
// violations are expected everywhere.
// Colour contrast and target size cannot be measured in jsdom (no layout, no computed colours), so those two
// rules are off; the contrast is measured by hand and the 24x24 target size is kept by the `min-h-6`/`min-w-6`
// classes (WCAG 2.2 AA 2.5.8). Every other axe rule stays on.
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import axe from 'axe-core';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { ROUTE_PATHS, type RoutePath } from '@/app/routes';
import { tr } from '@/i18n/tr';
import { trc } from '@/i18n/tr-catalog';
import { DecisionForm } from '@/review/decision-form';
import { BaglantiQueue } from '@/screens/baglanti/baglanti-queue';
import { ok, problem, useFakeApi } from './fake-api';
import { EDITOR_EMAIL, page, reviewDetail, session, signedIn, unitDetail } from './fixtures';
import {
  ARABIC_SAMPLE,
  aliasDetail,
  aliasItem,
  TANZIL_FARK,
  xrefHandlers,
  xrefItem,
  type AliasSpec,
} from './fixtures-baglanti-sure';
import {
  RELEASE_GATE_REPORT,
  releaseDetail,
  releaseItem,
  releasePage,
  source,
} from './fixtures-catalog';
import {
  ocrDetail,
  ocrHandlers,
  ocrItem,
  ocrUnit,
  pipelineProposal,
  stubCanvas,
  stubObjectUrls,
  syntheticTiff,
  withScanFetch,
  type CanvasStub,
  type ObjectUrlStub,
} from './fixtures-ocr';
import { renderApp, renderInRouter, renderWithProviders } from './render-app';

async function violations(container: HTMLElement): Promise<string[]> {
  const result = await axe.run(container, {
    rules: { 'color-contrast': { enabled: false }, 'target-size': { enabled: false } },
  });
  return result.violations.map(
    (violation) =>
      `${violation.id}: ${violation.nodes.map((node) => node.target.join(' ')).join(' | ')}`,
  );
}

const HEADINGS: Record<RoutePath, string> = {
  '/giris': tr.session.loginTitle,
  '/kuyruk/ocr': tr.nav.queueOcr,
  '/kuyruk/lemma': tr.nav.queueLemma,
  '/kuyruk/baglanti': tr.nav.queueBaglanti,
  '/kuyruk/sure-adi': tr.nav.queueSureAdi,
  '/kaynaklar': tr.nav.sources,
  '/birimler': tr.nav.units,
  '/yayinlar': tr.nav.releases,
};

/** The test id each protected screen shows once its (empty) list has been answered. */
const EMPTY_STATE: Record<Exclude<RoutePath, '/giris'>, string> = {
  '/kuyruk/ocr': 'queue-empty',
  '/kuyruk/lemma': 'queue-empty',
  '/kuyruk/baglanti': 'queue-empty',
  '/kuyruk/sure-adi': 'queue-empty',
  '/kaynaklar': 'sources-empty',
  '/birimler': 'units-empty',
  '/yayinlar': 'releases-empty',
};

describe('axe: the harness itself', () => {
  it('does find a violation (an image without a text alternative, a button without a name)', async () => {
    const host = document.createElement('div');
    host.innerHTML = '<img src="deneme.png"><button type="button"></button>';
    document.body.append(host);
    try {
      const found = await violations(host);
      expect(found.some((line) => line.startsWith('image-alt'))).toBe(true);
      expect(found.some((line) => line.startsWith('button-name'))).toBe(true);
    } finally {
      host.remove();
    }
  });
});

describe('axe: the eight routes with empty data', () => {
  const fake = useFakeApi();

  it('has one entry per route', () => {
    expect(ROUTE_PATHS).toHaveLength(8);
    expect(Object.keys(HEADINGS).sort()).toEqual([...ROUTE_PATHS].sort());
  });

  it.each(ROUTE_PATHS)('%s', async (path) => {
    if (path === '/giris') {
      fake.get('/api/v1/auth/me', problem(401, 'oturum-acilamadi'));
    } else {
      signedIn(fake);
    }
    const { container } = renderApp(fake, path);
    await screen.findByRole('heading', { level: 1, name: HEADINGS[path] });
    if (path !== '/giris') await screen.findByTestId(EMPTY_STATE[path]);
    expect(await violations(container)).toEqual([]);
  });
});

describe('axe: details', () => {
  const fake = useFakeApi();
  let canvas: CanvasStub;
  let urls: ObjectUrlStub;

  beforeEach(() => {
    canvas = stubCanvas();
    urls = stubObjectUrls();
  });
  afterEach(() => {
    canvas.restore();
    urls.restore();
  });

  it('the OCR card: ayah, meal, scan viewer, word difference and the decision form', async () => {
    // `/reviews/{id}` must be registered before `signedIn` registers `/reviews/stats`.
    ocrHandlers(fake, { detail: (id) => ocrDetail(id) });
    signedIn(fake);
    fake.get('/api/v1/reviews', ok(page([ocrItem(1), ocrItem(2)])));
    const scan = withScanFetch(fake, () => ({
      body: syntheticTiff(2, 1),
      contentType: 'image/tiff',
    }));
    const { container } = renderApp(scan, '/kuyruk/ocr?kayit=1');
    await screen.findByTestId('scan-canvas');
    await screen.findByTestId('ocr-unit-text');
    await screen.findByRole('radio', { name: tr.review.approve });
    expect(await violations(container)).toEqual([]);
  });

  it('the meal queue: source tabs, stage view, source and edition labels on the rows', async () => {
    ocrHandlers(fake, { detail: (id) => ocrDetail(id) });
    signedIn(fake);
    fake.get(
      '/api/v1/reviews',
      ok(
        page([
          ocrItem(1, { hedef_anahtar: 'meal:elmalili:2:1' }),
          ocrItem(2, { hedef_anahtar: 'meal:elmalili-sade:2:1', dogrulanmamis: true }),
        ]),
      ),
    );
    const { container } = renderApp(fake, '/kuyruk/ocr');
    expect(await screen.findAllByTestId('ocr-source')).toHaveLength(2);
    expect(await violations(container)).toEqual([]);
  });

  it('the meal card: source line, warning, witness agreement, covered range and basmala meal', async () => {
    const proposal = pipelineProposal({ uyari: ['birlesik_meal', 'kod_bilinmiyor'] });
    ocrHandlers(fake, {
      detail: (id) =>
        ocrDetail(id, {
          hedef_anahtar: 'meal:elmalili-sade:2:1',
          onceki: null,
          onerilen: proposal,
        }),
      unit: (anchor) =>
        ocrUnit(anchor, {
          attrs: {
            kapsam: 'q:2:1-2',
            besmele_meali: { metin: 'Deneme besmele meali', content_hash: 'hash-b' },
          },
        }),
    });
    signedIn(fake);
    fake.get(
      '/api/v1/reviews',
      ok(page([ocrItem(1, { hedef_anahtar: 'meal:elmalili-sade:2:1', onerilen: proposal })])),
    );
    const { container } = renderApp(fake, '/kuyruk/ocr?kayit=1');
    await screen.findByTestId('ocr-hat-warning');
    await screen.findByTestId('ocr-witness');
    await screen.findByTestId('ocr-besmele');
    await screen.findByTestId('ocr-ayah-scope');
    await screen.findByRole('radio', { name: tr.review.approve });
    expect(await violations(container)).toEqual([]);
  });

  it('the follower card of a joined meal: head link, closed Düzelt and the decision form', async () => {
    ocrHandlers(fake, {
      detail: (id) =>
        ocrDetail(id, { hedef_anahtar: 'meal:elmalili:2:2', onceki: null, onerilen: null }),
      unit: (anchor) =>
        ocrUnit(anchor, { metin: '', attrs: { birlesik_ile: 'meal:elmalili:2:1' } }),
    });
    signedIn(fake);
    fake.get(
      '/api/v1/reviews',
      ok(page([ocrItem(1, { hedef_anahtar: 'meal:elmalili:2:2', onerilen: null })])),
    );
    const { container } = renderApp(fake, '/kuyruk/ocr?kayit=1');
    await screen.findByTestId('ocr-follower');
    await screen.findByTestId('ocr-follower-fix');
    await screen.findByRole('radio', { name: tr.review.approve });
    expect(await violations(container)).toEqual([]);
  });

  it('the surah name card: groups, risk badge, Tanzil difference and the bulk panel', async () => {
    const specs: AliasSpec[] = [
      { id: 1, sure: 10, alias: 'Deneme-sure-10', anlam: 'Deneme anlamı on' },
      {
        id: 2,
        sure: 2,
        alias: 'Deneme-sure-2',
        anlam: 'Deneme anlamı iki',
        tanzilFark: TANZIL_FARK,
      },
      { id: 3, sure: 2, alias: 'Riskli-deneme', kind: 'diger_ad', risky: true },
    ];
    fake.get('/api/v1/reviews/{id}', (call) =>
      ok(aliasDetail(specs.find((spec) => spec.id === Number(call.params.id))!)),
    );
    signedIn(fake);
    fake.get('/api/v1/reviews', ok(page(specs.map(aliasItem))));
    const { container } = renderApp(fake, '/kuyruk/sure-adi');
    expect(await screen.findAllByTestId('sure-adi-card')).toHaveLength(3);
    expect(await violations(container)).toEqual([]);
  });

  it('the unit detail: text, marks, hash and the correction form', async () => {
    signedIn(fake);
    fake.get('/api/v1/units/{anchor}', ok(unitDetail({ duzeltilebilir: true })));
    const { container } = renderApp(fake, '/birimler?birim=rn%3Adeneme%3Ap1');
    await screen.findByTestId('unit-text');
    expect(await violations(container)).toEqual([]);
  });

  it('the release detail: gate report, summaries and the admin actions', async () => {
    signedIn(fake, ['admin']);
    fake.get('/api/v1/releases', ok(releasePage([releaseItem()])));
    fake.get('/api/v1/releases/{id}', ok(releaseDetail({ kapi_raporu: RELEASE_GATE_REPORT })));
    const { container } = renderApp(fake, '/yayinlar?yayin=7');
    await screen.findByRole('article');
    await screen.findByRole('button', { name: trc.releases.promote });
    expect(await violations(container)).toEqual([]);
  });

  it('the source detail', async () => {
    signedIn(fake);
    const record = source();
    fake.get('/api/v1/sources', ok([record]));
    fake.get('/api/v1/sources/{slug}', ok(record));
    const { container } = renderApp(fake, '/kaynaklar?kaynak=test-deneme');
    await screen.findByRole('article');
    expect(await violations(container)).toEqual([]);
  });
});

describe('axe: the link candidates queue (full card and the 10 percent sample panel)', () => {
  const fake = useFakeApi();

  /** The queue on its own router with a list of `count` synthetic candidates; the bulk flag is injected. */
  function setupQueue(count: number, route: string, bulkEnabled?: boolean) {
    const list = Array.from({ length: count }, (_, index) => xrefItem(index + 1));
    fake.get('/api/v1/reviews', ok(page(list)));
    xrefHandlers(fake);
    fake.get('/api/v1/auth/me', ok(session()));
    return renderInRouter(fake, <BaglantiQueue bulkEnabled={bulkEnabled} />, route);
  }

  it('the full card: evidence, four missing sections, closed buttons and the decision form', async () => {
    const { container } = setupQueue(2, '/?kayit=1');
    // Evidence: paragraph, candidate ayah (Arabic, as stored) and meal, all loaded.
    await screen.findByText('Deneme paragrafı 1');
    await screen.findByText('Deneme meal metni 1');
    expect(await screen.findByText(ARABIC_SAMPLE)).toHaveAttribute('lang', 'ar');
    // The closed buttons and the decision form are on screen.
    expect(container.querySelectorAll('[data-open-question]').length).toBeGreaterThan(0);
    await screen.findByRole('radio', { name: tr.review.approve });
    expect(screen.getByRole('button', { name: tr.review.submit })).toBeInTheDocument();
    expect(await violations(container)).toEqual([]);
  });

  it('the list with the bulk flag injected on and nothing selected: a checkbox on every row', async () => {
    const { container } = setupQueue(12, '/', true);
    expect(await screen.findAllByRole('checkbox')).toHaveLength(12);
    expect(await violations(container)).toEqual([]);
  });

  it('the sample panel with the bulk flag injected on: bar, radio groups and the evidence of each sampled row', async () => {
    const { container, user } = setupQueue(12, '/', true);
    const boxes = await screen.findAllByRole('checkbox');
    expect(boxes).toHaveLength(12);
    // 11 rows selected: ceil(11 / 10) = 2 sample rows with their radio groups.
    for (const box of boxes.slice(0, 11)) await user.click(box);
    const rows = await screen.findAllByTestId('bulk-sample-row');
    expect(rows).toHaveLength(2);
    for (const row of rows) {
      await within(row).findByText('Deneme paragrafı 1');
      await within(row).findByText(ARABIC_SAMPLE);
    }
    expect(screen.getAllByRole('radio', { name: tr.bulk.correct })).toHaveLength(2);
    expect(await violations(container)).toEqual([]);
  });
});

describe('axe: the decision form showing a 412 difference', () => {
  const fake = useFakeApi();

  it('has no violation with the stale-record difference, the kept input and the retained choice', async () => {
    const original = reviewDetail({ id: 5, xmin: 100 });
    const fresh = reviewDetail({
      id: 5,
      xmin: 101,
      onerilen: { metin: 'Deneme paragrafı 1 başka düzeltme', content_hash: 'hash-9' },
    });
    fake.get('/api/v1/auth/me', ok(session(['editor'], EDITOR_EMAIL)));
    fake.get('/api/v1/units/{anchor}', ok(unitDetail()));
    fake.post('/api/v1/reviews/{id}/decision', problem(412, 'surum-uyusmazligi'));
    fake.get('/api/v1/reviews/{id}', ok(fresh));
    const { container, user } = renderWithProviders(
      fake,
      <DecisionForm review={original} onDecided={() => {}} />,
    );
    await user.click(screen.getByRole('radio', { name: tr.review.approve }));
    fireEvent.change(await screen.findByLabelText(tr.review.editedText), {
      target: { value: 'Benim düzeltmem' },
    });
    await user.type(screen.getByLabelText(tr.review.reason), 'Deneme gerekçe');
    await user.click(screen.getByRole('button', { name: tr.review.submit }));
    await screen.findByTestId('stale-record');
    expect(await violations(container)).toEqual([]);
  });
});

describe('axe: error and loading states', () => {
  const fake = useFakeApi();

  it('a failed list shows the problem and the retry button', async () => {
    signedIn(fake);
    fake.get('/api/v1/reviews', problem(500, 'sunucu-hatasi'));
    const { container } = renderApp(fake, '/kuyruk/lemma');
    await screen.findByText(tr.queue.loadFailed);
    await screen.findByRole('button', { name: tr.ui.retry });
    expect(await violations(container)).toEqual([]);
  });

  it('a failed detail shows the problem', async () => {
    signedIn(fake);
    fake.get('/api/v1/reviews', ok(page([ocrItem(1)])));
    fake.get('/api/v1/reviews/{id}', problem(404, 'bulunamadi'));
    const { container } = renderApp(fake, '/kuyruk/baglanti?kayit=1');
    await screen.findByText(tr.queue.detailFailed);
    expect(await violations(container)).toEqual([]);
  });

  it('a failed unit list on the units screen', async () => {
    signedIn(fake);
    fake.get('/api/v1/units', problem(503, 'depo-erisilemiyor'));
    const { container } = renderApp(fake, '/birimler');
    await screen.findByRole('button', { name: tr.ui.retry });
    expect(await violations(container)).toEqual([]);
  });

  it('a list that is still loading (skeleton) and a detail that is still loading', async () => {
    let release: () => void = () => {};
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    signedIn(fake);
    fake.get('/api/v1/reviews', async () => {
      await gate;
      return ok(page([ocrItem(1)]));
    });
    fake.get('/api/v1/reviews/{id}', async () => {
      await gate;
      return ok(reviewDetail({ id: 1 }));
    });
    const { container } = renderApp(fake, '/kuyruk/baglanti?kayit=1');
    await screen.findByTestId('queue-loading');
    expect(await violations(container)).toEqual([]);
    release();
    // The detail skeleton shows once the list is there and the detail is still pending.
    await waitFor(() => expect(screen.queryByTestId('queue-loading')).toBeNull());
  });
});

describe('axe: login and 403 pages', () => {
  const fake = useFakeApi();

  it('the login page with the logout note after a sign-out', async () => {
    const { container } = renderApp(fake, '/giris?cikis=1');
    await screen.findByTestId('logged-out-note');
    expect(await violations(container)).toEqual([]);
  });

  it('the login page showing a wrong password message', async () => {
    fake.get('/api/v1/auth/me', problem(401, 'oturum-acilamadi'));
    fake.post('/api/v1/auth/login', problem(401, 'oturum-acilamadi'));
    const { container, user } = renderApp(fake, '/giris');
    await user.type(await screen.findByLabelText(tr.session.email), 'baska@deneme.test');
    await user.type(screen.getByLabelText(tr.session.password), 'yanlis');
    await user.click(screen.getByRole('button', { name: tr.session.submit }));
    await screen.findByText(tr.problem.contexts.login['oturum-acilamadi']);
    expect(await violations(container)).toEqual([]);
  });

  it('the no-permission page', async () => {
    fake.get('/api/v1/auth/me', problem(403, 'yetki-yok'));
    const { container } = renderApp(fake, '/kuyruk/lemma');
    await screen.findByRole('heading', { level: 1, name: tr.session.forbiddenTitle });
    expect(await violations(container)).toEqual([]);
  });

  it('the not-found screen inside the shell', async () => {
    signedIn(fake);
    const { container } = renderApp(fake, '/yok-boyle-bir-sayfa');
    await screen.findByRole('heading', { level: 1, name: tr.ui.notFoundTitle });
    expect(await violations(container)).toEqual([]);
  });
});
