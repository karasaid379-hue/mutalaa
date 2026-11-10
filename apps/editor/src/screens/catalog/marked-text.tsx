import { Fragment, useId } from 'react';
import { ArabicText } from '@/components/arabic-text';
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { trc } from '@/i18n/tr-catalog';
import { cn } from '@/lib/utils';
import { cpLength, layoutMarks, prettyJson, readMarks, type MarkEntry } from './readers';

export interface MarkedTextProps {
  /** The canonical text exactly as stored; it is rendered as is (no trim, no normalization; K-26). */
  text: string;
  /** `unit.marks` as the API returns it (opaque JSON); unreadable or invalid entries are not drawn. */
  marks: unknown;
  /** Arabic text (`ayet` unit or a `kuran_metni` source): right to left with the Quran font. */
  arabic?: boolean;
  className?: string;
}

/**
 * The text of a unit with its `marks` laid over it: a range is wrapped in a `mark` element, a zero-width
 * mark is a thin bar. Offsets are Unicode code points and ranges are half open (`[s, e)`); they are converted
 * to UTF-16 only to cut the text, and the joined parts always give back the stored text. The marks are
 * listed in `MarksTable` too, so nothing is carried by the highlight alone.
 */
export function MarkedText({ text, marks, arabic = false, className }: MarkedTextProps) {
  const entries = readMarks(marks, cpLength(text)) ?? [];
  const { segments, points } = layoutMarks(text, entries);
  const drawn = segments.some((segment) => segment.marks.length > 0) || points.length > 0;

  const body = drawn
    ? [
        ...segments.map((segment, position) => (
          <Fragment key={`segment-${position}`}>
            {points
              .filter((point) => point.before === position)
              .map((point) => (
                <PointMark key={`point-${point.index}`} index={point.index} />
              ))}
            {segment.marks.length > 0 ? (
              <mark
                data-marks={segment.marks.join(' ')}
                title={trc.units.markedBy(segment.marks.join(', '))}
                className="bg-accent text-accent-foreground underline decoration-dotted underline-offset-4"
              >
                {segment.text}
              </mark>
            ) : (
              segment.text
            )}
          </Fragment>
        )),
        ...points
          .filter((point) => point.before >= segments.length)
          .map((point) => <PointMark key={`point-${point.index}`} index={point.index} />),
      ]
    : text;

  return arabic ? (
    <ArabicText as="div" className={cn('text-xl', className)}>
      {body}
    </ArabicText>
  ) : (
    <p className={cn('break-words whitespace-pre-wrap', className)}>{body}</p>
  );
}

function PointMark({ index }: { index: number }) {
  return (
    <span
      aria-hidden="true"
      data-mark-point={index}
      title={trc.units.markedBy(String(index))}
      className="mx-px inline-block h-[1em] w-0.5 bg-primary align-middle"
    />
  );
}

/** The marks as a table: number, type, offsets and the anchor of a footnote; invalid ranges are flagged. */
export function MarksTable({ marks, textLength }: { marks: unknown; textLength: number }) {
  const headingId = useId();
  const entries = readMarks(marks, textLength);
  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-1">
      <h3 id={headingId} className="text-sm font-medium">
        {trc.units.marks}
      </h3>
      {entries === null ? (
        <div className="flex flex-col gap-1">
          <p className="text-sm">{trc.units.marksUnreadable}</p>
          <pre className="max-h-48 overflow-auto rounded-lg border p-2 text-xs whitespace-pre-wrap">
            {prettyJson(marks)}
          </pre>
        </div>
      ) : entries.length === 0 ? (
        <p className="text-sm text-muted-foreground">{trc.units.marksNone}</p>
      ) : (
        <Table>
          <TableCaption>{trc.units.marksNote}</TableCaption>
          <TableHeader>
            <TableRow>
              <TableHead>{trc.units.markIndex}</TableHead>
              <TableHead>{trc.units.markType}</TableHead>
              <TableHead>{trc.units.markStart}</TableHead>
              <TableHead>{trc.units.markEnd}</TableHead>
              <TableHead>{trc.units.markAnchor}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {entries.map((entry) => (
              <MarkRow key={entry.index} entry={entry} />
            ))}
          </TableBody>
        </Table>
      )}
    </section>
  );
}

function MarkRow({ entry }: { entry: MarkEntry }) {
  return (
    <TableRow data-mark-valid={entry.valid ? 'true' : 'false'}>
      <TableCell>{entry.index}</TableCell>
      <TableCell className="whitespace-normal">
        {entry.type}
        {entry.valid ? null : ` · ${trc.units.markInvalid}`}
      </TableCell>
      <TableCell>{entry.start ?? ''}</TableCell>
      <TableCell>{entry.end ?? trc.units.markPoint}</TableCell>
      <TableCell className="font-mono break-all whitespace-normal">{entry.anchor ?? ''}</TableCell>
    </TableRow>
  );
}
