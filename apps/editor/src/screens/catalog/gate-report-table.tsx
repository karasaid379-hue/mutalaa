import { useId } from 'react';
import { ScrollRegion } from '@/components/scroll-region';
import { Badge } from '@/components/ui/badge';
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
import { trc } from '@/i18n/tr-catalog';
import { formatNumber } from '@/lib/format';
import { isEmptyReport, prettyJson, readGateReport } from './readers';

export interface GateReportTableProps {
  /** `kapi_raporu` of a release or of a preview: opaque JSON, read at run time. */
  report: unknown;
  className?: string;
}

/**
 * The quality gate report (K-46, `GateReport.ToJson`): the decision per package, source, unit group, link
 * group and dictionary group (entered or not, rule code, reason) and the integrity violations that reject
 * a release. The decision is always written out; colour never carries the meaning alone.
 */
export function GateReportTable({ report, className }: GateReportTableProps) {
  const headingId = useId();
  const data = readGateReport(report);

  return (
    <section aria-labelledby={headingId} className={className}>
      <h3 id={headingId} className="text-sm font-medium">
        {trc.gate.heading}
      </h3>
      {isEmptyReport(report) ? (
        <p className="text-sm text-muted-foreground">{trc.gate.none}</p>
      ) : data === null ? (
        <div className="flex flex-col gap-1">
          <p className="text-sm">{trc.gate.unreadable}</p>
          <ScrollRegion
            label={trc.common.scrollArea(trc.gate.heading)}
            dir="ltr"
            className="max-h-64 overflow-auto rounded-lg border p-2 text-xs whitespace-pre-wrap"
          >
            {prettyJson(report)}
          </ScrollRegion>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          <p className="flex flex-wrap items-center gap-2 text-sm">
            <Badge variant={data.rejected ? 'destructive' : 'secondary'}>
              {data.rejected ? trc.gate.rejected : trc.gate.accepted}
            </Badge>
            {data.flavor ? (
              <span>{`${trc.gate.flavor}: ${labelOf(trc.flavor, data.flavor)}`}</span>
            ) : null}
          </p>

          <div>
            <Table>
              <TableCaption>{trc.gate.rowsCaption}</TableCaption>
              <TableHeader>
                <TableRow>
                  <TableHead>{trc.gate.kind}</TableHead>
                  <TableHead>{trc.gate.id}</TableHead>
                  <TableHead>{trc.gate.decision}</TableHead>
                  <TableHead>{trc.gate.rule}</TableHead>
                  <TableHead>{trc.gate.reason}</TableHead>
                  <TableHead>{trc.gate.count}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.rows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6}>{trc.gate.rowsNone}</TableCell>
                  </TableRow>
                ) : (
                  data.rows.map((row, position) => (
                    <TableRow
                      key={`${row.kind}:${row.id}:${row.decision}:${row.rule ?? ''}:${position}`}
                    >
                      <TableCell>{labelOf(trc.gate.kinds, row.kind)}</TableCell>
                      <TableCell className="font-mono break-all whitespace-normal">
                        {row.id}
                      </TableCell>
                      <TableCell>
                        <Badge variant={row.decision === 'girmedi' ? 'outline' : 'secondary'}>
                          {labelOf(trc.gate.decisions, row.decision)}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono">{row.rule ?? trc.gate.noRule}</TableCell>
                      <TableCell className="whitespace-normal">{row.reason}</TableCell>
                      <TableCell>{formatNumber(row.count)}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          <div>
            <Table>
              <TableCaption>{trc.gate.violationsCaption}</TableCaption>
              <TableHeader>
                <TableRow>
                  <TableHead>{trc.gate.rule}</TableHead>
                  <TableHead>{trc.gate.subject}</TableHead>
                  <TableHead>{trc.gate.reason}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.violations.length === 0 && data.omitted.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={3}>{trc.gate.violationsNone}</TableCell>
                  </TableRow>
                ) : (
                  <>
                    {data.violations.map((violation, position) => (
                      <TableRow key={`${violation.rule ?? ''}:${violation.subject}:${position}`}>
                        <TableCell className="font-mono">
                          {violation.rule ?? trc.gate.noRule}
                        </TableCell>
                        <TableCell className="font-mono break-all whitespace-normal">
                          {violation.subject}
                        </TableCell>
                        <TableCell className="whitespace-normal">{violation.reason}</TableCell>
                      </TableRow>
                    ))}
                    {data.omitted.map((omission, position) => (
                      <TableRow key={`omitted:${omission.rule ?? ''}:${position}`}>
                        <TableCell colSpan={3} className="whitespace-normal">
                          {trc.gate.omitted(
                            omission.count,
                            omission.rule ?? trc.gate.noRule,
                            omission.reason,
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </>
                )}
              </TableBody>
            </Table>
          </div>
        </div>
      )}
    </section>
  );
}
