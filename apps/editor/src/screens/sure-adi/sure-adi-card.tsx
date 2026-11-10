import { TriangleAlertIcon } from 'lucide-react';
import { Link } from 'react-router';
import { ArabicText } from '@/components/arabic-text';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { labelOf } from '@/i18n/labels';
import { trSureAdi } from '@/i18n/tr-baglanti-sure';
import { cn } from '@/lib/utils';
import { ReviewBadges } from '@/review/badges';
import type { SourceRef, SureAdiRow, TanzilFark } from './payload';

function describeSource(ref: SourceRef): string {
  const parts: string[] = [];
  if (ref.kaynak) parts.push(ref.kaynak);
  if (ref.dosya) parts.push(`${trSureAdi.file}: ${ref.dosya}`);
  if (ref.yol) parts.push(ref.yol);
  if (ref.alan) parts.push(ref.alan);
  if (ref.kural) parts.push(ref.kural);
  if (ref.satir !== null) parts.push(`${trSureAdi.line} ${ref.satir}`);
  return parts.join(' · ');
}

/** The Tanzil difference warning: an icon, a heading and a table, so the colour is never the only signal. */
function TanzilFarkNote({ fark }: { fark: TanzilFark }) {
  return (
    <div
      className="flex flex-col gap-1 rounded-md border border-l-4 border-destructive/60 p-2 text-sm"
      data-testid="tanzil-fark"
    >
      <p className="flex items-center gap-1 font-medium text-destructive">
        <TriangleAlertIcon aria-hidden="true" className="size-4 shrink-0" />
        {trSureAdi.tanzilFarkTitle}
      </p>
      <p className="text-xs text-muted-foreground">{trSureAdi.tanzilFarkHint}</p>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{trSureAdi.tanzilField}</TableHead>
            <TableHead>{trSureAdi.tanzilWikipedia}</TableHead>
            <TableHead>{trSureAdi.tanzilTanzil}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {fark.alanlar.map((alan) => {
            const key = alan as keyof typeof fark.vikipedi;
            const known = Object.hasOwn(fark.vikipedi, alan);
            return (
              <TableRow key={alan}>
                <TableCell>{labelOf(trSureAdi.labels.tanzilField, alan)}</TableCell>
                <TableCell>{known ? (fark.vikipedi[key] ?? '') : ''}</TableCell>
                <TableCell>{known ? (fark.tanzil[key] ?? '') : ''}</TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

export interface SureAdiCardProps {
  row: SureAdiRow;
  /** The row is checked for the bulk approval. */
  checked: boolean;
  onToggle: (id: number, checked: boolean) => void;
  /** This record is open on the right. */
  current: boolean;
  /** The bulk approval flagged this row (stale, missing, rule violation). */
  marked: boolean;
}

/**
 * One candidate on its card: every field the editor needs is on the card (the bulk approval has no sample).
 * Risky names (and rows whose risk could not be read) have no checkbox: they are decided one by one.
 */
export function SureAdiCard({ row, checked, onToggle, current, marked }: SureAdiCardProps) {
  const { item, payload, alias } = row;
  const arabic = payload?.kind === 'arapca';
  return (
    <li
      className={cn('flex flex-col gap-2 rounded-lg border p-3', current && 'border-primary')}
      data-testid="sure-adi-card"
    >
      <div className="flex items-start gap-2">
        {row.selectable ? (
          <Checkbox
            aria-label={trSureAdi.selectRow(alias)}
            checked={checked}
            onCheckedChange={(value) => onToggle(item.id, value)}
            className="mt-1"
          />
        ) : null}
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <Link
            to={{ search: `?kayit=${item.id}` }}
            aria-current={current ? 'true' : undefined}
            className="min-h-6 font-medium break-words underline-offset-4 hover:underline"
          >
            {arabic ? <ArabicText text={alias} className="text-xl" /> : alias}
          </Link>
          <span className="flex flex-wrap items-center gap-1">
            {payload?.kind ? (
              <Badge variant="outline">{labelOf(trSureAdi.labels.kind, payload.kind)}</Badge>
            ) : null}
            {payload?.risky === true ? (
              <Badge variant="destructive">
                <TriangleAlertIcon aria-hidden="true" />
                {trSureAdi.riskyBadge}
              </Badge>
            ) : null}
            <ReviewBadges review={item} />
          </span>
        </div>
      </div>

      {payload === null ? (
        <p className="text-sm text-muted-foreground">{trSureAdi.noPayload}</p>
      ) : null}
      {payload?.risky === true ? (
        <p className="text-sm">{trSureAdi.riskyOnlySingle}</p>
      ) : payload !== null && payload.risky === null ? (
        <p className="text-sm">{trSureAdi.riskUnknownOnlySingle}</p>
      ) : null}

      {payload?.anlam ? (
        <p className="text-sm">
          <span className="text-muted-foreground">{`${trSureAdi.anlam}: `}</span>
          {payload.anlam}
        </p>
      ) : null}

      {payload?.tanzilFark ? <TanzilFarkNote fark={payload.tanzilFark} /> : null}

      {payload && payload.yazimlar.length > 0 ? (
        <div className="text-sm">
          <p className="text-muted-foreground">{trSureAdi.yazimlar}</p>
          <ul className="flex flex-wrap gap-x-3 gap-y-1">
            {payload.yazimlar.map((spelling, index) => (
              <li key={`${index}:${spelling}`}>
                {arabic ? <ArabicText text={spelling} className="text-lg" /> : spelling}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {payload && payload.kaynaklar.length > 0 ? (
        <div className="text-xs text-muted-foreground">
          <p>{trSureAdi.kaynaklar}</p>
          <ul className="list-disc pl-4">
            {payload.kaynaklar.map((ref, index) => (
              <li key={index}>{describeSource(ref)}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {marked ? <p className="text-sm text-destructive">{trSureAdi.rowMarked}</p> : null}
    </li>
  );
}
