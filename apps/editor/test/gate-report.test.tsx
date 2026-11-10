import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { trc } from '@/i18n/tr-catalog';
import { GateReportTable } from '@/screens/catalog/gate-report-table';
import { readGateReport } from '@/screens/catalog/readers';
import { RELEASE_GATE_REPORT } from './fixtures-catalog';

describe('GateReportTable', () => {
  it('shows every row with kind, id, decision, rule, reason and count', () => {
    render(<GateReportTable report={RELEASE_GATE_REPORT} />);
    const rows = screen.getByRole('table', { name: trc.gate.rowsCaption });
    const body = within(rows).getAllByRole('row').slice(1);
    expect(body).toHaveLength(3);

    const paket = within(body[0]!).getAllByRole('cell');
    expect(paket[0]).toHaveTextContent(trc.gate.kinds.paket);
    expect(paket[1]).toHaveTextContent('deneme-paket');
    expect(paket[2]).toHaveTextContent(trc.gate.decisions.girdi);
    expect(paket[3]).toHaveTextContent(trc.gate.noRule);

    const kaynak = within(body[1]!).getAllByRole('cell');
    expect(kaynak[0]).toHaveTextContent(trc.gate.kinds.kaynak);
    expect(kaynak[2]).toHaveTextContent(trc.gate.decisions.girmedi);
    expect(kaynak[3]).toHaveTextContent('P-07');
    expect(kaynak[4]).toHaveTextContent('deneme gerekçe');

    // Counts are formatted for tr-TR.
    expect(within(body[2]!).getAllByRole('cell')[5]).toHaveTextContent('1.500');
  });

  it('states the result in words, not by colour alone', () => {
    const { rerender } = render(<GateReportTable report={RELEASE_GATE_REPORT} />);
    expect(screen.getByText(trc.gate.rejected)).toBeInTheDocument();
    rerender(<GateReportTable report={{ ...RELEASE_GATE_REPORT, rejected: false }} />);
    expect(screen.getByText(trc.gate.accepted)).toBeInTheDocument();
    expect(screen.getByText(`${trc.gate.flavor}: ${trc.flavor.internal}`)).toBeInTheDocument();
  });

  it('lists the violations and the count of the ones the report left out', () => {
    render(<GateReportTable report={RELEASE_GATE_REPORT} />);
    const table = screen.getByRole('table', { name: trc.gate.violationsCaption });
    expect(within(table).getByText('rn:deneme:p1')).toBeInTheDocument();
    expect(
      within(table).getByText(trc.gate.omitted(7, 'P-11', 'deneme ihlal')),
    ).toBeInTheDocument();
  });

  it('says so when there is no violation', () => {
    render(
      <GateReportTable
        report={{
          ...RELEASE_GATE_REPORT,
          rejected: false,
          violations: [],
          violations_omitted: [],
        }}
      />,
    );
    expect(screen.getByText(trc.gate.violationsNone)).toBeInTheDocument();
  });

  it('shows an empty report ({}) as "not there yet"', () => {
    render(<GateReportTable report={{}} />);
    expect(screen.getByText(trc.gate.none)).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('shows an unreadable report as raw JSON instead of guessing', () => {
    render(<GateReportTable report={{ rejected: 'evet', rows: 'yok' }} />);
    expect(screen.getByText(trc.gate.unreadable)).toBeInTheDocument();
    expect(screen.getByText(/"rows": "yok"/)).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('shows an unknown kind or decision raw', () => {
    const report = {
      ...RELEASE_GATE_REPORT,
      violations: [],
      violations_omitted: [],
      rows: [{ kind: 'yeni-tur', id: 'x', decision: 'belki', rule: 'P-99', reason: 'r', count: 2 }],
    };
    render(<GateReportTable report={report} />);
    expect(screen.getByText('yeni-tur')).toBeInTheDocument();
    expect(screen.getByText('belki')).toBeInTheDocument();
  });

  it('keeps the heading as an h3 of a labelled section', () => {
    render(<GateReportTable report={RELEASE_GATE_REPORT} />);
    expect(screen.getByRole('region', { name: trc.gate.heading })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 3, name: trc.gate.heading })).toBeInTheDocument();
  });
});

describe('readGateReport', () => {
  it('reads the documented shape', () => {
    const data = readGateReport(RELEASE_GATE_REPORT);
    expect(data?.rejected).toBe(true);
    expect(data?.rows).toHaveLength(3);
    expect(data?.omitted).toEqual([{ rule: 'P-11', reason: 'deneme ihlal', count: 7 }]);
  });

  it('accepts a report without violations_omitted (below the limit the field is not written)', () => {
    const { violations_omitted, ...report } = RELEASE_GATE_REPORT;
    void violations_omitted;
    expect(readGateReport(report)?.omitted).toEqual([]);
  });

  it.each([
    [null],
    ['metin'],
    [[]],
    [{ rows: [] }],
    [{ rejected: false }],
    [{ rejected: false, rows: [1] }],
  ])('returns null for %j', (value) => {
    expect(readGateReport(value)).toBeNull();
  });
});
