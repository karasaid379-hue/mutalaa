import { NavLink } from 'react-router';
import { useApi } from '@/app/api-context';
import { Badge } from '@/components/ui/badge';
import { tr } from '@/i18n/tr';
import { formatNumber } from '@/lib/format';
import { cn } from '@/lib/utils';
import { REVIEW_STATS_PATH } from '@/review/queries';
import { QUEUES, openCount, type QueueId } from '@/review/queues';

const QUEUE_LABELS: Record<QueueId, string> = {
  ocr: tr.nav.queueOcr,
  lemma: tr.nav.queueLemma,
  baglanti: tr.nav.queueBaglanti,
  'sure-adi': tr.nav.queueSureAdi,
};

const PAGES = [
  { path: '/kaynaklar', label: tr.nav.sources },
  { path: '/birimler', label: tr.nav.units },
  { path: '/yayinlar', label: tr.nav.releases },
] as const;

function linkClass({ isActive }: { isActive: boolean }): string {
  return cn(
    'flex min-h-6 items-center justify-between gap-2 rounded-lg px-2 py-1 text-sm hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none',
    isActive && 'bg-muted font-medium',
  );
}

/**
 * Navigation of the app shell. The queue entries show the number of open records from
 * `GET /reviews/stats`; there is no count per editor (K-25: no leaderboard). Below the `lg` breakpoint it sits on
 * top of the page and its entries wrap (WCAG 1.4.10 reflow); from `lg` up it is the 14rem column on the left.
 */
export function Sidebar() {
  const api = useApi();
  const stats = api.$api.useQuery('get', REVIEW_STATS_PATH, undefined, { staleTime: 15_000 });
  return (
    <nav
      aria-label={tr.nav.label}
      className="flex w-full shrink-0 flex-col gap-3 border-b p-3 lg:w-56 lg:gap-4 lg:border-r lg:border-b-0"
    >
      <div>
        <h2 className="mb-1 px-2 text-xs font-medium text-muted-foreground uppercase">
          {tr.nav.queues}
        </h2>
        <ul className="flex flex-wrap gap-1 lg:flex-col">
          {QUEUES.map((queue) => {
            const count = openCount(stats.data, queue);
            return (
              <li key={queue.id}>
                <NavLink to={queue.path} className={linkClass}>
                  <span>{QUEUE_LABELS[queue.id]}</span>
                  {count !== undefined ? (
                    <Badge variant="secondary">
                      <span>{formatNumber(count)}</span>
                      <span className="sr-only">{tr.nav.openSuffix}</span>
                    </Badge>
                  ) : null}
                </NavLink>
              </li>
            );
          })}
        </ul>
        {stats.isError ? (
          <p className="px-2 pt-1 text-xs text-muted-foreground">{tr.nav.statsFailed}</p>
        ) : null}
      </div>
      <div>
        <h2 className="mb-1 px-2 text-xs font-medium text-muted-foreground uppercase">
          {tr.nav.pages}
        </h2>
        <ul className="flex flex-wrap gap-1 lg:flex-col">
          {PAGES.map((page) => (
            <li key={page.path}>
              <NavLink to={page.path} className={linkClass}>
                {page.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </div>
    </nav>
  );
}
