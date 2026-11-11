import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, type ReactNode } from 'react';
import { Link } from 'react-router';
import { useAnnounce } from '@/app/announce-context';
import { useApi } from '@/app/api-context';
import { ProblemMessage } from '@/components/problem-message';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { labelOf } from '@/i18n/labels';
import { tr } from '@/i18n/tr';
import { trc } from '@/i18n/tr-catalog';
import { formatDateTime } from '@/lib/format';
import { GateReportTable } from './gate-report-table';
import { JsonBlock } from './json-block';
import { isPreparing, pollInterval } from './polling';
import { ReleaseRequestButtons, type ReleaseAccepted } from './release-actions';
import { readDigests, type DigestEntry } from './readers';

const RELEASE_PATH = '/api/v1/releases/{id}' as const;
const RELEASES_PATH = '/api/v1/releases' as const;

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5 sm:grid sm:grid-cols-[12rem_minmax(0,1fr)] sm:gap-3">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="min-w-0 text-sm">{children}</dd>
    </div>
  );
}

function DigestTable({ caption, entries }: { caption: string; entries: DigestEntry[] }) {
  return (
    <Table>
      <TableCaption>{caption}</TableCaption>
      <TableHeader>
        <TableRow>
          <TableHead>{trc.releases.digestName}</TableHead>
          <TableHead>{trc.releases.digestValue}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {entries.length === 0 ? (
          <TableRow>
            <TableCell colSpan={2}>{trc.releases.digestsNone}</TableCell>
          </TableRow>
        ) : (
          entries.map((entry) => (
            <TableRow key={entry.name}>
              <TableCell className="font-mono break-all whitespace-normal">{entry.name}</TableCell>
              <TableCell className="font-mono break-all whitespace-normal">
                {entry.digest}
              </TableCell>
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  );
}

export interface ReleaseDetailPaneProps {
  id: number;
  /** Polling switch of the screen (the user can stop it). */
  autoRefresh: boolean;
  /** Admin role: the promote and rollback buttons are only drawn for it. */
  canPublish: boolean;
  onAccepted: (accepted: ReleaseAccepted) => void;
  releaseHref: (id: number) => string;
  /** Reports whether the loaded release is still being prepared (the screen draws the polling switch). */
  onPreparingChange: (preparing: boolean) => void;
}

/**
 * Detail of one release (`GET /releases/{id}`): the states, the quality gate report, the digests and the
 * manifest. While the release is `hazirlaniyor` it is read again every 5 seconds (stopped by the user,
 * and never while the tab is hidden); the list is refreshed when the state changes.
 */
export function ReleaseDetailPane({
  id,
  autoRefresh,
  canPublish,
  onAccepted,
  releaseHref,
  onPreparingChange,
}: ReleaseDetailPaneProps) {
  const api = useApi();
  const announce = useAnnounce();
  const queryClient = useQueryClient();
  const detail = api.$api.useQuery(
    'get',
    RELEASE_PATH,
    { params: { path: { id } } },
    {
      retry: false,
      refetchInterval: (query) => pollInterval(autoRefresh, isPreparing(query.state.data?.durum)),
    },
  );
  const release = detail.data;
  const durum = release?.durum;
  const preparing = isPreparing(durum);

  useEffect(() => {
    onPreparingChange(preparing);
    return () => onPreparingChange(false);
  }, [preparing, onPreparingChange]);

  // A state change seen by polling: say it once and bring the list up to date.
  const lastDurum = useRef<string | undefined>(undefined);
  useEffect(() => {
    const before = lastDurum.current;
    lastDurum.current = durum;
    if (before === undefined || durum === undefined || before === durum) return;
    announce(trc.releases.statusChanged(labelOf(trc.releaseStatus, durum)));
    void queryClient.invalidateQueries({ queryKey: ['get', RELEASES_PATH] });
  }, [durum, announce, queryClient]);

  if (detail.isPending) {
    return (
      <div className="flex flex-col gap-2" data-testid="release-detail-loading">
        <Skeleton className="h-8" />
        <Skeleton className="h-32" />
      </div>
    );
  }
  if (detail.isError) {
    return (
      <div className="flex flex-col gap-2">
        <p className="text-sm font-medium">{trc.releases.detailFailed}</p>
        <ProblemMessage error={detail.error} />
        <div>
          <Button type="button" variant="outline" onClick={() => void detail.refetch()}>
            {tr.ui.retry}
          </Button>
        </div>
      </div>
    );
  }
  if (!release) return null;

  const digests = readDigests(release.ozetler);
  return (
    <article className="flex flex-col gap-4" aria-labelledby="release-title">
      <header className="flex flex-col gap-1">
        <h2 id="release-title" className="text-lg font-semibold">
          {trc.releases.rowTitle(release.id, release.surum)}
        </h2>
        <p className="flex flex-wrap items-center gap-2 text-sm">
          <Badge variant="secondary">{labelOf(trc.flavor, release.derleme)}</Badge>
          <Badge variant={release.durum === 'basarisiz' ? 'destructive' : 'outline'}>
            {labelOf(trc.releaseStatus, release.durum)}
          </Badge>
          <Badge variant="outline">{labelOf(trc.request, release.talep)}</Badge>
        </p>
        {preparing ? <p className="text-sm">{trc.releases.preparing}</p> : null}
      </header>

      <dl className="flex flex-col gap-2">
        <Row label={trc.releases.version}>{release.surum}</Row>
        <Row label={trc.releases.flavor}>{labelOf(trc.flavor, release.derleme)}</Row>
        <Row label={trc.releases.status}>{labelOf(trc.releaseStatus, release.durum)}</Row>
        <Row label={trc.releases.request}>{labelOf(trc.request, release.talep)}</Row>
        <Row label={trc.releases.creator}>{release.olusturan}</Row>
        <Row label={trc.releases.createdAt}>{formatDateTime(release.created_at)}</Row>
        <Row label={trc.releases.publishedAt}>
          {release.yayinlandi_at ? formatDateTime(release.yayinlandi_at) : trc.common.none}
        </Row>
        <Row label={trc.releases.dataVersion}>{release.data_version}</Row>
        <Row label={trc.releases.packs}>
          {release.paketler && release.paketler.length > 0 ? (
            <span className="font-mono break-all">{release.paketler.join(', ')}</span>
          ) : (
            trc.releases.allPacks
          )}
        </Row>
        <Row label={trc.releases.sourceRelease}>
          {release.kaynak_release_id !== null ? (
            <Link to={{ search: releaseHref(release.kaynak_release_id) }} className="underline">
              {String(release.kaynak_release_id)}
            </Link>
          ) : (
            trc.common.none
          )}
        </Row>
        <Row label={trc.releases.notes}>
          {release.notlar ? (
            <span dir="auto" className="whitespace-pre-wrap">
              {release.notlar}
            </span>
          ) : (
            trc.common.none
          )}
        </Row>
      </dl>

      {canPublish ? (
        <ReleaseRequestButtons
          release={release}
          onAccepted={onAccepted}
          releaseHref={releaseHref}
        />
      ) : null}

      <GateReportTable report={release.kapi_raporu} />

      <section className="flex flex-col gap-2" aria-labelledby="release-digests">
        <h3 id="release-digests" className="text-sm font-medium">
          {trc.releases.digests}
        </h3>
        {digests === null ? (
          <>
            <p className="text-sm">{trc.releases.digestsUnreadable}</p>
            <JsonBlock title={trc.common.rawJson} value={release.ozetler} />
          </>
        ) : (
          <>
            <DigestTable caption={trc.releases.sourceDigests} entries={digests.sources} />
            <DigestTable caption={trc.releases.packDigests} entries={digests.packs} />
          </>
        )}
      </section>

      <section className="flex flex-col gap-1" aria-labelledby="release-manifest">
        <h3 id="release-manifest" className="text-sm font-medium">
          {trc.releases.manifest}
        </h3>
        {release.manifest === null || release.manifest === undefined ? (
          <p className="text-sm text-muted-foreground">{trc.releases.manifestNone}</p>
        ) : (
          <JsonBlock title={trc.releases.manifestShow} value={release.manifest} />
        )}
      </section>
    </article>
  );
}
