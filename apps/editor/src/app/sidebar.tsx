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
    'flex min-h-6 items-center justify-between gap-2 rounded-lg px-2 py-1 text-sm hover:bg-muted',
    isActive && 'bg-muted font-medium',
  );
}

/**
 * Navigation of the app shell. The queue entries show the number of open records from
 * `GET /reviews/stats`; there is no count per editor (K-25: no leaderboard).
 */
export function Sidebar() {
  const api = useApi();
  const stats = api.$api.useQuery('get', REVIEW_STATS_PATH, undefined, { staleTime: 15_000 });
  return (
    <nav aria-label={tr.nav.label} className="flex w-56 shrink-0 flex-col gap-4 border-r p-3">
      <div>
        <h2 className="mb-1 px-2 text-xs font-medium text-muted-foreground uppercase">
          {tr.nav.queues}
        </h2>
        <ul className="flex flex-col gap-1">
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
        <ul className="flex flex-col gap-1">
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
