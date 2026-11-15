import { CircleDashedIcon, LayersIcon, ShapesIcon, SplitIcon } from 'lucide-react';
import { useId, type ComponentType } from 'react';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { trBaglanti } from '@/i18n/tr-baglanti-sure';
import type { LinkClass } from '@/review/queries';
import type { ReviewStats } from '@/review/types';
import {
  LINK_CLASSES,
  LINK_STATUS_VIEWS,
  isLinkClass,
  isLinkStatusView,
  type LinkStatusView,
} from './config';
import { classCount, readLinkClass } from './link-snapshot';

const CLASS_ICONS: Record<LinkClass, ComponentType<{ 'aria-hidden'?: 'true' }>> = {
  tutarsiz: SplitIcon,
  toplu: LayersIcon,
  gri: CircleDashedIcon,
  diger: ShapesIcon,
};

/**
 * The class of a link candidate as a badge: the meaning is in the text and the icon, never in the colour alone.
 * Its explanation is hidden text tied with `aria-describedby`. A record without a known class shows no badge (the
 * value is never guessed).
 */
export function ClassBadge({ sinif }: { sinif: string | null | undefined }) {
  const hintId = useId();
  const read = readLinkClass(sinif);
  if (read === null) return null;
  const Icon = CLASS_ICONS[read];
  return (
    <>
      <Badge
        variant={read === 'tutarsiz' ? 'destructive' : 'outline'}
        aria-describedby={hintId}
        data-testid="class-badge"
        data-link-class={read}
      >
        <Icon aria-hidden="true" />
        {trBaglanti.classes[read]}
      </Badge>
      <span id={hintId} className="sr-only">
        {trBaglanti.classHints[read]}
      </span>
    </>
  );
}

interface ClassFilterProps {
  value: LinkClass | 'hepsi';
  onChange: (value: LinkClass | 'hepsi') => void;
  stats: ReviewStats | undefined;
}

/** "Sınıf: Hepsi | Tutarsız (n) | Toplu uygun (n) | Gri bölge (n) | Diğer (n)": the server filters (`sinif`). */
export function ClassFilter({ value, onChange, stats }: ClassFilterProps) {
  const hintId = useId();
  return (
    <div className="flex flex-col gap-1" data-testid="link-class-filter">
      <RadioGroup
        aria-label={trBaglanti.classFilter.label}
        aria-describedby={hintId}
        value={value}
        className="flex flex-wrap items-center gap-x-4 gap-y-1"
        onValueChange={(next) => {
          if (next === 'hepsi' || isLinkClass(next)) onChange(next);
        }}
      >
        <span className="text-sm font-medium" aria-hidden="true">
          {trBaglanti.classLabel}
        </span>
        <Label className="min-h-6 gap-2 font-normal">
          <RadioGroupItem value="hepsi" />
          {trBaglanti.classFilter.all}
        </Label>
        {LINK_CLASSES.map((entry) => {
          const count = classCount(stats, entry);
          return (
            <Label key={entry} className="min-h-6 gap-2 font-normal">
              <RadioGroupItem value={entry} />
              {count === undefined
                ? trBaglanti.classes[entry]
                : trBaglanti.classFilter.count(trBaglanti.classes[entry], count)}
            </Label>
          );
        })}
      </RadioGroup>
      <p id={hintId} className="text-xs text-muted-foreground">
        {trBaglanti.classFilter.note}
      </p>
    </div>
  );
}

interface StatusViewProps {
  value: LinkStatusView;
  onChange: (value: LinkStatusView) => void;
  stats: ReviewStats | undefined;
}

/** "Kayıtlar: Açık | Uzmanda (n)": the open records or those sent to an expert (`durum=uzmanda`). */
export function StatusView({ value, onChange, stats }: StatusViewProps) {
  return (
    <div className="flex flex-col gap-1" data-testid="link-status-view">
      <RadioGroup
        aria-label={trBaglanti.statusView.label}
        value={value}
        className="flex flex-wrap items-center gap-x-4 gap-y-1"
        onValueChange={(next) => {
          if (isLinkStatusView(next)) onChange(next);
        }}
      >
        <span className="text-sm font-medium" aria-hidden="true">
          {trBaglanti.statusView.label}
        </span>
        {LINK_STATUS_VIEWS.map((entry) => (
          <Label key={entry} className="min-h-6 gap-2 font-normal">
            <RadioGroupItem value={entry} />
            {entry === 'uzmanda' && stats
              ? trBaglanti.statusView.uzmandaCount(
                  trBaglanti.statusView.uzmanda,
                  stats.toplam_uzmanda,
                )
              : trBaglanti.statusView[entry]}
          </Label>
        ))}
      </RadioGroup>
      {value === 'uzmanda' ? (
        <p className="text-xs text-muted-foreground">{trBaglanti.statusView.uzmandaNote}</p>
      ) : null}
    </div>
  );
}
