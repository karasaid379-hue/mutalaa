import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { components } from '@/api/schema';
import { tr } from '@/i18n/tr';
import { trSureAdi } from '@/i18n/tr-baglanti-sure';
import { SureAdiQueue } from '@/screens/sure-adi/sure-adi-queue';
import { ok, problem, useFakeApi } from './fake-api';
import {
  ARABIC_SAMPLE,
  TANZIL_FARK,
  aliasDetail,
  aliasItem,
  type AliasSpec,
} from './fixtures-baglanti-sure';
import { page, session, signedIn } from './fixtures';
import { renderApp, renderInRouter } from './render-app';

type Item = components['schemas']['ReviewItemDto'];

const SPECS: AliasSpec[] = [
  { id: 1, sure: 10, alias: 'Deneme-sure-10', anlam: 'Deneme anlamı on' },
  { id: 2, sure: 2, alias: 'Deneme-sure-2-yazim', kind: 'yazim' },
  { id: 3, sure: 2, alias: 'Deneme-sure-2', anlam: 'Deneme anlamı iki', tanzilFark: TANZIL_FARK },
  { id: 4, sure: 2, alias: 'Riskli-deneme', kind: 'diger_ad', risky: true },
  { id: 5, sure: 2, alias: ARABIC_SAMPLE, kind: 'arapca', yazimlar: ['Deneme-yazim-5'] },
  { id: 6, sure: 10, alias: 'Deneme-sure-10-b', kind: 'yazim', risky: false },
];

const groups = () => screen.getAllByTestId('sure-adi-group');
async function groupOf(sure: number): Promise<HTMLElement> {
  const all = await screen.findAllByTestId('sure-adi-group');
  return all.find((group) =>
    within(group).queryByRole('heading', { name: trSureAdi.groupHeading(sure) }),
  )!;
}
const reasonField = () => screen.getByLabelText(tr.bulk.reason);

describe('SureAdiQueue', () => {
  const fake = useFakeApi();
  const listCalls = () => fake.callsTo('get', '/api/v1/reviews');
  const bulkCalls = () => fake.callsTo('post', '/api/v1/reviews/decisions');
  const singleCalls = () => fake.callsTo('post', '/api/v1/reviews/{id}/decision');

  /** The list answers from `store` (so a decided record leaves it); the detail comes from the specs. */
  function setup(specs: AliasSpec[] = SPECS, route = '/') {
    let store: Item[] = specs.map(aliasItem);
    fake.get('/api/v1/reviews', () => ok(page(store)));
    fake.get('/api/v1/reviews/{id}', (call) => {
      const spec = specs.find((entry) => entry.id === Number(call.params.id))!;
      return ok(aliasDetail(spec));
    });
    fake.get('/api/v1/auth/me', ok(session()));
    fake.post('/api/v1/reviews/decisions', (call) => {
      const kararlar = (call.json as { kararlar: { id: number }[] }).kararlar;
      store = store.filter((item) => !kararlar.some((entry) => entry.id === item.id));
      return ok({
        sonuclar: kararlar.map((entry) => ({
          id: entry.id,
          durum: 'onaylandi',
          eylem: 'onayla',
          xmin: 2000 + entry.id,
        })),
      });
    });
    fake.post('/api/v1/reviews/{id}/decision', (call) => {
      const id = Number(call.params.id);
      store = store.filter((item) => item.id !== id);
      return ok({
        id,
        durum: (call.json as { karar: string }).karar,
        eylem: 'onayla',
        ikinci_onay_bekliyor: false,
        hedef_durumu: 'onayli',
        xmin: 3000 + id,
      });
    });
    return renderInRouter(fake, <SureAdiQueue />, route);
  }

  describe('loading', () => {
    it('sends the first request without a cursor, with the filter and 200 per page', async () => {
      setup();
      await screen.findByText(trSureAdi.groupHeading(2));
      const first = listCalls()[0]!;
      expect(first.search.has('cursor')).toBe(false);
      expect(first.search.get('hedef_tablo')).toBe('surah_alias');
      expect(first.search.get('alan')).toBe('status');
      expect(first.search.get('durum')).toBe('acik');
      expect(first.search.get('limit')).toBe('200');
    });

    it('fetches every page without a button and groups all of them', async () => {
      fake.get('/api/v1/reviews', (call) => {
        const cursor = call.search.get('cursor');
        if (cursor === 'b') return ok(page([aliasItem(SPECS[3]!)], null));
        if (cursor === 'a') return ok(page([aliasItem(SPECS[1]!), aliasItem(SPECS[2]!)], 'b'));
        return ok(page([aliasItem(SPECS[0]!)], 'a'));
      });
      renderInRouter(fake, <SureAdiQueue />);
      await screen.findByText('Riskli-deneme');
      expect(listCalls()).toHaveLength(3);
      expect(listCalls().map((call) => call.search.get('cursor'))).toEqual([null, 'a', 'b']);
      expect(listCalls().every((call) => call.search.get('limit') === '200')).toBe(true);
      expect(screen.queryByRole('button', { name: tr.ui.loadMore })).not.toBeInTheDocument();
      // The sure 2 group holds the records of the pages 2 and 3 together.
      expect(within(await groupOf(2)).getAllByTestId('sure-adi-card')).toHaveLength(3);
    });

    it('shows the empty state', async () => {
      fake.get('/api/v1/reviews', ok(page([])));
      renderInRouter(fake, <SureAdiQueue />);
      expect(await screen.findByTestId('queue-empty')).toHaveTextContent(tr.queue.empty);
      expect(screen.queryAllByTestId('sure-adi-group')).toHaveLength(0);
    });

    it('shows the problem and a retry button when the list fails, and recovers', async () => {
      let fail = true;
      fake.get('/api/v1/reviews', () =>
        fail ? problem(500, 'sunucu-hatasi') : ok(page([aliasItem(SPECS[0]!)])),
      );
      const { user } = renderInRouter(fake, <SureAdiQueue />);
      expect(await screen.findByText(tr.queue.loadFailed)).toBeInTheDocument();
      expect(screen.getByText(tr.problem.codes['sunucu-hatasi'])).toBeInTheDocument();
      fail = false;
      await user.click(screen.getByRole('button', { name: tr.ui.retry }));
      expect(await screen.findByText('Deneme-sure-10')).toBeInTheDocument();
    });
  });

  describe('groups and cards', () => {
    it('orders the groups by the surah number and the cards by kind and name', async () => {
      setup();
      await screen.findByText(trSureAdi.groupHeading(2));
      expect(groups().map((group) => within(group).getByRole('heading').textContent)).toEqual([
        trSureAdi.groupHeading(2),
        trSureAdi.groupHeading(10),
      ]);
      const names = (group: HTMLElement) =>
        within(group)
          .getAllByTestId('sure-adi-card')
          .map((card) => within(card).getAllByRole('link')[0]!.textContent);
      expect(names(await groupOf(2))).toEqual([
        'Deneme-sure-2',
        'Deneme-sure-2-yazim',
        'Riskli-deneme',
        ARABIC_SAMPLE,
      ]);
      expect(names(await groupOf(10))).toEqual(['Deneme-sure-10', 'Deneme-sure-10-b']);
    });

    it('puts every field on the card: kind, meaning, spellings, sources', async () => {
      setup();
      const group = await groupOf(2);
      const cards = await within(group).findAllByTestId('sure-adi-card');
      const canonical = cards[0]!;
      expect(within(canonical).getByText(trSureAdi.labels.kind.kanonik)).toBeInTheDocument();
      expect(within(canonical).getByText('Deneme anlamı iki')).toBeInTheDocument();
      expect(
        within(canonical).getByText(
          `deneme-kaynak · ${trSureAdi.file}: deneme-liste.txt · ${trSureAdi.line} 3`,
        ),
      ).toBeInTheDocument();
      const arabic = cards[3]!;
      expect(within(arabic).getByText('Deneme-yazim-5')).toBeInTheDocument();
      expect(within(arabic).getByText(trSureAdi.yazimlar)).toBeInTheDocument();
      expect(within(arabic).getByText(trSureAdi.labels.kind.arapca)).toBeInTheDocument();
    });

    it('draws an Arabic name with lang and dir and unchanged', async () => {
      setup();
      const group = await groupOf(2);
      const link = await within(group).findByRole('link', { name: ARABIC_SAMPLE });
      const text = link.querySelector('[lang="ar"]')!;
      expect(text).toHaveAttribute('dir', 'rtl');
      expect(text.textContent).toBe(ARABIC_SAMPLE);
    });

    it('warns about a Tanzil difference with a heading, an icon and a table (not by colour alone)', async () => {
      setup();
      const note = await screen.findByTestId('tanzil-fark');
      expect(within(note).getByText(trSureAdi.tanzilFarkTitle)).toBeInTheDocument();
      expect(note.querySelector('svg')).toHaveAttribute('aria-hidden', 'true');
      const rows = within(note).getAllByRole('row');
      // Header and two differing fields (ayet, yer); the field names are Turkish labels.
      expect(rows).toHaveLength(3);
      expect(
        within(rows[1]!)
          .getAllByRole('cell')
          .map((cell) => cell.textContent),
      ).toEqual([trSureAdi.labels.tanzilField.ayet, '7', '8']);
      expect(
        within(rows[2]!)
          .getAllByRole('cell')
          .map((cell) => cell.textContent),
      ).toEqual([trSureAdi.labels.tanzilField.yer, 'deneme-yer-a', 'deneme-yer-b']);
      // Only the card with a difference carries the warning.
      expect(screen.getAllByTestId('tanzil-fark')).toHaveLength(1);
    });

    it('marks a risky name with a text badge and a note, and gives it no checkbox', async () => {
      setup();
      const group = await groupOf(2);
      const cards = await within(group).findAllByTestId('sure-adi-card');
      const risky = cards[2]!;
      expect(within(risky).getByText(trSureAdi.riskyBadge)).toBeInTheDocument();
      expect(within(risky).getByText(trSureAdi.riskyOnlySingle)).toBeInTheDocument();
      expect(within(risky).queryByRole('checkbox')).not.toBeInTheDocument();
      expect(within(cards[0]!).getByRole('checkbox')).toBeInTheDocument();
      expect(screen.getAllByText(trSureAdi.riskyBadge)).toHaveLength(1);
    });

    it('treats a row whose risk cannot be read as risky and shows a malformed payload raw', async () => {
      setup([
        { id: 1, sure: 3, alias: 'Belirsiz-deneme', risky: null },
        { id: 2, sure: 3, alias: 'x', onerilen: { degisik: true } },
      ]);
      const cards = await screen.findAllByTestId('sure-adi-card');
      expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
      expect(within(cards[0]!).getAllByRole('link')[0]).toHaveTextContent(/Belirsiz-deneme|3:x/);
      expect(screen.getAllByText(trSureAdi.riskUnknownOnlySingle)).toHaveLength(2);
    });

    it('shows the unverified badge only from the API field', async () => {
      const specs = [{ id: 1, sure: 3, alias: 'Deneme-sure-3' }];
      fake.get(
        '/api/v1/reviews',
        ok(page([{ ...aliasItem(specs[0]!), dogrulanmamis: true, yz_modeli: 'deneme-model' }])),
      );
      renderInRouter(fake, <SureAdiQueue />);
      const card = await screen.findByTestId('sure-adi-card');
      expect(within(card).getByText(tr.badge.unverified)).toBeInTheDocument();
    });
  });

  describe('bulk approval', () => {
    it('"Grubu seç" selects the non-risky names of that group only', async () => {
      const { user } = setup();
      const group = await groupOf(2);
      await user.click(await within(group).findByRole('button', { name: trSureAdi.selectGroup }));
      const boxes = within(group).getAllByRole('checkbox');
      // Canonical, spelling and Arabic rows are checked; the risky row has no box at all.
      expect(boxes).toHaveLength(3);
      expect(boxes.every((box) => box.getAttribute('aria-checked') === 'true')).toBe(true);
      expect(screen.getByTestId('sure-adi-bulk')).toHaveTextContent(trSureAdi.selectedCount(3));
      expect(screen.getByTestId('bulk-count')).toHaveTextContent(tr.bulk.count(3));
      // The other group is untouched.
      const other = await groupOf(10);
      expect(
        within(other)
          .getAllByRole('checkbox')
          .every((box) => box.getAttribute('aria-checked') === 'false'),
      ).toBe(true);
      // The same button now clears the selection.
      await user.click(within(group).getByRole('button', { name: trSureAdi.clearGroup }));
      expect(screen.queryByTestId('sure-adi-bulk')).not.toBeInTheDocument();
    });

    it('a group with no selectable name has no "Grubu seç" button', async () => {
      setup([{ id: 1, sure: 5, alias: 'Riskli-deneme', risky: true }]);
      const group = (await screen.findAllByTestId('sure-adi-group'))[0]!;
      expect(within(group).queryByRole('button')).not.toBeInTheDocument();
      expect(within(group).getByText(trSureAdi.noSelectable)).toBeInTheDocument();
    });

    it('has no sample: every selected row is on its card and no verdict is asked', async () => {
      const { user } = setup();
      const group = await groupOf(2);
      await user.click(await within(group).findByRole('button', { name: trSureAdi.selectGroup }));
      const bulk = screen.getByTestId('sure-adi-bulk');
      expect(within(bulk).getByText(tr.bulk.noSampling)).toBeInTheDocument();
      expect(screen.queryByTestId('bulk-sample')).not.toBeInTheDocument();
      expect(screen.queryAllByTestId('bulk-sample-row')).toHaveLength(0);
      expect(within(bulk).queryByRole('radio')).not.toBeInTheDocument();
    });

    it('offers approval only: no reject control in the bulk bar', async () => {
      const { user } = setup();
      await user.click(
        within(await groupOf(2)).getByRole('button', {
          name: trSureAdi.selectGroup,
        }),
      );
      const bulk = screen.getByTestId('sure-adi-bulk');
      expect(within(bulk).getByText(tr.bulk.onlyApprove)).toBeInTheDocument();
      expect(
        within(bulk).queryByRole('button', { name: tr.review.reject }),
      ).not.toBeInTheDocument();
      expect(within(bulk).queryByRole('radio', { name: tr.review.reject })).not.toBeInTheDocument();
      expect(within(bulk).getByRole('button', { name: tr.bulk.confirm })).toBeInTheDocument();
    });

    it('sends one approval for the selected names without any risky one, then they leave the list', async () => {
      const { user } = setup();
      const group = await groupOf(2);
      await user.click(await within(group).findByRole('button', { name: trSureAdi.selectGroup }));
      // One more name from another group.
      await user.click(
        screen.getByRole('checkbox', { name: trSureAdi.selectRow('Deneme-sure-10-b') }),
      );
      fireEvent.change(reasonField(), { target: { value: 'Deneme gerekçesi' } });
      await user.click(screen.getByRole('button', { name: tr.bulk.confirm }));
      await waitFor(() => expect(bulkCalls()).toHaveLength(1));
      const call = bulkCalls()[0]!;
      expect(call.headers.has('If-Match')).toBe(false);
      const body = call.json as { kararlar: { id: number; xmin: number; karar: string }[] };
      expect(body.kararlar.map((entry) => entry.id).sort()).toEqual([2, 3, 5, 6]);
      expect(body.kararlar.every((entry) => entry.karar === 'onaylandi')).toBe(true);
      expect(body.kararlar.find((entry) => entry.id === 3)!.xmin).toBe(903);
      expect(body.kararlar.map((entry) => entry.id)).not.toContain(4);
      // The decided names left the list; the risky one and the unselected one stay.
      await waitFor(() =>
        expect(screen.queryByText('Deneme-sure-2-yazim')).not.toBeInTheDocument(),
      );
      expect(screen.getByText('Riskli-deneme')).toBeInTheDocument();
      expect(screen.getByText('Deneme-sure-10')).toBeInTheDocument();
      expect(screen.queryByTestId('sure-adi-bulk')).not.toBeInTheDocument();
    });

    it('does not send a bulk request without a reason', async () => {
      const { user } = setup();
      await user.click(
        await within(await groupOf(2)).findByRole('button', {
          name: trSureAdi.selectGroup,
        }),
      );
      await user.click(screen.getByRole('button', { name: tr.bulk.confirm }));
      expect(await screen.findByTestId('bulk-summary')).toHaveTextContent(tr.review.reasonRequired);
      expect(bulkCalls()).toHaveLength(0);
    });
  });

  describe('single decision', () => {
    it('opens a risky name from its card and decides it one by one with If-Match', async () => {
      const { user, router } = setup();
      await user.click(await screen.findByRole('link', { name: 'Riskli-deneme' }));
      expect(router.state.location.search).toBe('?kayit=4');
      const approve = await screen.findByRole('radio', { name: tr.review.approve });
      await user.click(approve);
      fireEvent.change(screen.getByLabelText(tr.review.reason), {
        target: { value: 'Tek tek denetlendi' },
      });
      await user.click(screen.getByRole('button', { name: tr.review.submit }));
      await waitFor(() => expect(singleCalls()).toHaveLength(1));
      const call = singleCalls()[0]!;
      expect(call.params.id).toBe('4');
      expect(call.headers.get('If-Match')).toBe('"904"');
      expect(call.json).toEqual({
        karar: 'onaylandi',
        duzenlenen: null,
        gerekce: 'Tek tek denetlendi',
      });
      expect(bulkCalls()).toHaveLength(0);
    });

    it('rejects one by one', async () => {
      const { user } = setup();
      await user.click(await screen.findByRole('link', { name: 'Deneme-sure-10' }));
      await user.click(await screen.findByRole('radio', { name: tr.review.reject }));
      fireEvent.change(screen.getByLabelText(tr.review.reason), {
        target: { value: 'Yanlış yazım' },
      });
      await user.click(screen.getByRole('button', { name: tr.review.submit }));
      await waitFor(() => expect(singleCalls()).toHaveLength(1));
      expect((singleCalls()[0]!.json as { karar: string }).karar).toBe('reddedildi');
      expect(bulkCalls()).toHaveLength(0);
    });

    it('opens the next card in the display order after a decision and starts with an empty form', async () => {
      const { user, router } = setup();
      await user.click(await screen.findByRole('link', { name: 'Deneme-sure-2' }));
      await user.click(await screen.findByRole('radio', { name: tr.review.approve }));
      fireEvent.change(screen.getByLabelText(tr.review.reason), { target: { value: 'Tamam' } });
      await user.click(screen.getByRole('button', { name: tr.review.submit }));
      // Display order: 3 (kanonik), 2 (yazim), ...; after 3 comes 2.
      await waitFor(() => expect(router.state.location.search).toBe('?kayit=2'));
      await waitFor(() =>
        expect(screen.getByRole('radio', { name: tr.review.approve })).not.toBeChecked(),
      );
      expect(screen.getByLabelText(tr.review.reason)).toHaveValue('');
    });

    it('shows the detail error when the record cannot be loaded', async () => {
      fake.get('/api/v1/reviews', ok(page([aliasItem(SPECS[0]!)])));
      fake.get('/api/v1/reviews/{id}', problem(404, 'bulunamadi'));
      renderInRouter(fake, <SureAdiQueue />, '/?kayit=1');
      expect(await screen.findByText(tr.queue.detailFailed)).toBeInTheDocument();
    });
  });

  describe('route', () => {
    it('is the sure adı route with the title as h1 and the queue behind the session', async () => {
      signedIn(fake);
      fake.get('/api/v1/reviews', ok(page([aliasItem(SPECS[0]!)])));
      renderApp(fake, '/kuyruk/sure-adi');
      expect(
        await screen.findByRole('heading', { level: 1, name: tr.nav.queueSureAdi }),
      ).toBeInTheDocument();
      expect(await screen.findByText('Deneme-sure-10')).toBeInTheDocument();
      const first = listCalls()[0]!;
      expect(first.search.get('hedef_tablo')).toBe('surah_alias');
    });
  });
});
