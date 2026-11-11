// axe-core pass over the catalog screens (kaynaklar, birimler, yayinlar) with their detail and form states.
// Colour contrast and target size cannot be measured in jsdom, so those two rules are off; they are checked by hand.
import { screen, within } from '@testing-library/react';
import axe from 'axe-core';
import { describe, expect, it } from 'vitest';
import { tr } from '@/i18n/tr';
import { trc } from '@/i18n/tr-catalog';
import { ok, useFakeApi } from './fake-api';
import { signedIn, unitDetail } from './fixtures';
import {
  RELEASE_GATE_REPORT,
  releaseDetail,
  releaseItem,
  releasePage,
  source,
  tanzilUnit,
  unitItem,
  unitPage,
} from './fixtures-catalog';
import { renderApp } from './render-app';

async function violations(container: HTMLElement): Promise<string[]> {
  const result = await axe.run(container, {
    rules: { 'color-contrast': { enabled: false }, 'target-size': { enabled: false } },
  });
  return result.violations.map(
    (violation) =>
      `${violation.id}: ${violation.nodes.map((node) => node.target.join(' ')).join(' | ')}`,
  );
}

describe('catalog screens: axe', () => {
  const fake = useFakeApi();

  it('sources: list and detail', async () => {
    signedIn(fake);
    const record = source();
    fake.get('/api/v1/sources', ok([record]));
    fake.get('/api/v1/sources/{slug}', ok(record));
    const { container } = renderApp(fake, '/kaynaklar?kaynak=test-deneme');
    await screen.findByRole('article');
    expect(await violations(container)).toEqual([]);
  });

  it('units: filters, list and a unit with marks, sentences and the correction form', async () => {
    signedIn(fake);
    fake.get(
      '/api/v1/units',
      ok(unitPage([unitItem(), unitItem({ anchor: 'q:1:1', kind: 'ayet' })])),
    );
    fake.get('/api/v1/units/{anchor}', ok(unitDetail({ duzeltilebilir: true })));
    const { container, user } = renderApp(fake, '/birimler?birim=rn%3Adeneme%3Ap1');
    await user.click(await screen.findByRole('button', { name: trc.units.correct }));
    await screen.findByRole('textbox', { name: trc.units.correctionText });
    expect(await violations(container)).toEqual([]);
  });

  it('units: a unit with marks and an immutable ayah', async () => {
    signedIn(fake);
    fake.get('/api/v1/units', ok(unitPage([])));
    fake.get(
      '/api/v1/units/{anchor}',
      ok(
        unitDetail({
          marks: [
            { s: 0, e: 4, t: 'ar' },
            { s: 6, t: 'hasiye' },
          ],
          sentences: [[0, 8]],
        }),
      ),
    );
    const view = renderApp(fake, '/birimler?birim=rn%3Adeneme%3Ap1');
    await screen.findByRole('button', { name: /Açık soru: A16/ });
    expect(await violations(view.container)).toEqual([]);
    view.unmount();

    fake.get('/api/v1/units/{anchor}', ok(tanzilUnit()));
    const second = renderApp(fake, '/birimler?birim=q%3A1%3A1');
    await screen.findByText(trc.units.immutableNote);
    expect(await violations(second.container)).toEqual([]);
  });

  it('units: an invalid anchor', async () => {
    signedIn(fake);
    fake.get('/api/v1/units', ok(unitPage([])));
    const { container } = renderApp(fake, '/birimler?birim=q%3A999%3A1');
    await screen.findByTestId('anchor-invalid');
    expect(await violations(container)).toEqual([]);
  });

  it('releases: list, detail with the gate report and the admin panel with its dialog', async () => {
    signedIn(fake, ['admin']);
    fake.get('/api/v1/releases', ok(releasePage([releaseItem()])));
    fake.get('/api/v1/releases/{id}', ok(releaseDetail({ kapi_raporu: RELEASE_GATE_REPORT })));
    const { container, user } = renderApp(fake, '/yayinlar?yayin=7');
    await screen.findByRole('article');
    await screen.findByRole('button', { name: trc.releases.promote });
    expect(await violations(container)).toEqual([]);

    await user.click(screen.getByRole('button', { name: trc.releases.promote }));
    const dialog = await screen.findByRole('alertdialog');
    expect(within(dialog).getByText(trc.releases.confirmPromoteTitle)).toBeInTheDocument();
    expect(await violations(document.body)).toEqual([]);
  });

  it('releases: the empty list', async () => {
    signedIn(fake);
    fake.get('/api/v1/releases', ok(releasePage([])));
    const { container } = renderApp(fake, '/yayinlar');
    await screen.findByTestId('releases-empty');
    expect(await violations(container)).toEqual([]);
    expect(screen.getByRole('heading', { level: 1, name: tr.nav.releases })).toBeInTheDocument();
  });
});
