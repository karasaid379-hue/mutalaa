import { useId, useState, type FormEvent } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { trc } from '@/i18n/tr-catalog';
import { codePointCount, isWritable } from '@/lib/text';
import type { Filters } from './unit-filter-types';

/** Server limit of `q` in code points (Backend API 4.1). */
const MAX_QUERY_LENGTH = 1024;

export function FilterForm({
  initial,
  onApply,
}: {
  initial: Filters;
  onApply: (filters: Filters) => void;
}) {
  const ids = {
    source: useId(),
    prefix: useId(),
    prefixHint: useId(),
    q: useId(),
    qHint: useId(),
    qError: useId(),
  };
  const [filters, setFilters] = useState<Filters>(initial);
  const [qError, setQError] = useState<string | null>(null);

  function apply(event: FormEvent) {
    event.preventDefault();
    if (!isWritable(filters.q)) {
      setQError(trc.units.queryUnwritable);
      return;
    }
    if (codePointCount(filters.q) > MAX_QUERY_LENGTH) {
      setQError(trc.units.queryTooLong(MAX_QUERY_LENGTH));
      return;
    }
    setQError(null);
    onApply(filters);
  }

  return (
    <>
      <form
        onSubmit={apply}
        className="flex flex-col gap-3"
        aria-label={trc.units.filterLegend}
        noValidate
      >
        <div className="flex flex-col gap-1">
          <Label htmlFor={ids.source}>{trc.units.source}</Label>
          <Input
            id={ids.source}
            value={filters.kaynak}
            onChange={(event) => setFilters({ ...filters, kaynak: event.target.value })}
            autoComplete="off"
            spellCheck={false}
          />
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor={ids.prefix}>{trc.units.prefix}</Label>
          <Input
            id={ids.prefix}
            value={filters.onek}
            onChange={(event) => setFilters({ ...filters, onek: event.target.value })}
            aria-describedby={ids.prefixHint}
            autoComplete="off"
            spellCheck={false}
          />
          <p id={ids.prefixHint} className="text-xs text-muted-foreground">
            {trc.units.prefixHint}
          </p>
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor={ids.q}>{trc.units.query}</Label>
          <Input
            id={ids.q}
            value={filters.q}
            onChange={(event) => setFilters({ ...filters, q: event.target.value })}
            aria-describedby={`${ids.qHint}${qError ? ` ${ids.qError}` : ''}`}
            aria-invalid={qError ? true : undefined}
            autoComplete="off"
          />
          <p id={ids.qHint} className="text-xs text-muted-foreground">
            {trc.units.queryHint}
          </p>
          {qError ? (
            <p id={ids.qError} className="text-xs text-destructive">
              {qError}
            </p>
          ) : null}
        </div>
        <div className="flex gap-2">
          <Button type="submit">{trc.units.apply}</Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              setFilters({ kaynak: '', onek: '', q: '' });
              setQError(null);
              onApply({ kaynak: '', onek: '', q: '' });
            }}
          >
            {trc.units.clear}
          </Button>
        </div>
      </form>
    </>
  );
}

export function AnchorForm({
  initial,
  onOpen,
}: {
  initial: string;
  onOpen: (anchor: string) => void;
}) {
  const ids = { anchor: useId(), hint: useId() };
  const [draft, setDraft] = useState(initial);

  function open(event: FormEvent) {
    event.preventDefault();
    // The anchor is used exactly as typed; an empty field does nothing.
    if (draft !== '') onOpen(draft);
  }

  return (
    <form
      onSubmit={open}
      className="flex flex-col gap-1"
      aria-label={trc.units.openAnchor}
      noValidate
    >
      <Label htmlFor={ids.anchor}>{trc.units.openAnchor}</Label>
      <div className="flex gap-2">
        <Input
          id={ids.anchor}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          aria-describedby={ids.hint}
          autoComplete="off"
          spellCheck={false}
          className="font-mono"
        />
        <Button type="submit" variant="outline">
          {trc.units.open}
        </Button>
      </div>
      <p id={ids.hint} className="text-xs text-muted-foreground">
        {trc.units.openAnchorHint}
      </p>
    </form>
  );
}
