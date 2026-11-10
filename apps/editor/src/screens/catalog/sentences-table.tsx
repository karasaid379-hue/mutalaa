import { useId } from 'react';
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
import { readSentences } from './readers';

/** The sentence ranges of a unit (`sentences`, code points, `[start, end)`); a range outside the text is flagged. */
export function SentencesTable({
  sentences,
  textLength,
}: {
  sentences: readonly (readonly number[])[] | null | undefined;
  textLength: number;
}) {
  const headingId = useId();
  const entries = readSentences(sentences, textLength);
  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-1">
      <h3 id={headingId} className="text-sm font-medium">
        {trc.units.sentences}
      </h3>
      {entries.length === 0 ? (
        <p className="text-sm text-muted-foreground">{trc.units.sentencesNone}</p>
      ) : (
        <Table>
          <TableCaption>{trc.units.sentencesCaption}</TableCaption>
          <TableHeader>
            <TableRow>
              <TableHead>{trc.units.sentenceIndex}</TableHead>
              <TableHead>{trc.units.sentenceStart}</TableHead>
              <TableHead>{trc.units.sentenceEnd}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {entries.map((entry) => (
              <TableRow key={entry.index} data-sentence-valid={entry.valid ? 'true' : 'false'}>
                <TableCell>
                  {entry.index}
                  {entry.valid ? null : ` · ${trc.units.sentenceInvalid}`}
                </TableCell>
                <TableCell>{entry.start}</TableCell>
                <TableCell>{entry.end}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </section>
  );
}
