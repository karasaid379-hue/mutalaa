import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Table, TableBody, TableCell, TableRow } from '@/components/ui/table';

function sample(scrollLabel?: string) {
  return (
    <Table scrollLabel={scrollLabel}>
      <TableBody>
        <TableRow>
          <TableCell>Deneme hücresi 1</TableCell>
        </TableRow>
      </TableBody>
    </Table>
  );
}

// WCAG 2.1.1: a scrolling area has to be reachable by keyboard.
describe('Table scroll container', () => {
  it('is a focusable named region when it has a scroll label', () => {
    render(sample('Deneme tablosu (kaydırılabilir alan)'));
    const region = screen.getByRole('region', { name: 'Deneme tablosu (kaydırılabilir alan)' });
    expect(region).toHaveAttribute('tabindex', '0');
    expect(region.querySelector('table')).not.toBeNull();
  });

  it('stays a plain container without a scroll label', () => {
    render(sample());
    expect(screen.queryByRole('region')).toBeNull();
    expect(document.querySelector('[data-slot="table-container"]')).not.toHaveAttribute('tabindex');
  });
});
