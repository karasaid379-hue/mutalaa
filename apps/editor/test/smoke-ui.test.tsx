// A15.2 smoke tests: Base UI based shadcn components work in jsdom (Select, Dialog, Toast).
import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it } from 'vitest';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Toaster, toast } from '@/components/ui/toast';

function SelectProbe() {
  const [value, setValue] = useState<string | null>(null);
  return (
    <>
      <Select value={value} onValueChange={setValue}>
        <SelectTrigger aria-label="deneme secimi">
          <SelectValue placeholder="sec" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="a">Deneme-a</SelectItem>
          <SelectItem value="b">Deneme-b</SelectItem>
        </SelectContent>
      </Select>
      <output data-testid="value">{value ?? 'yok'}</output>
    </>
  );
}

describe('shadcn (Base UI) smoke', () => {
  it('Select opens and selects an item', async () => {
    const user = userEvent.setup();
    render(<SelectProbe />);
    await user.click(screen.getByRole('combobox', { name: 'deneme secimi' }));
    await user.click(await screen.findByRole('option', { name: 'Deneme-b' }));
    await waitFor(() => expect(screen.getByTestId('value')).toHaveTextContent('b'));
  });

  it('Dialog opens, shows the Turkish close label and closes', async () => {
    const user = userEvent.setup();
    render(
      <Dialog>
        <DialogTrigger render={<Button />}>ac</DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Deneme baslik</DialogTitle>
            <DialogDescription>Deneme aciklama</DialogDescription>
          </DialogHeader>
          <DialogFooter showCloseButton />
        </DialogContent>
      </Dialog>,
    );
    await user.click(screen.getByRole('button', { name: 'ac' }));
    expect(await screen.findByRole('dialog', { name: 'Deneme baslik' })).toBeInTheDocument();
    const closeButtons = screen.getAllByRole('button', { name: 'Kapat' });
    expect(closeButtons.length).toBeGreaterThan(0);
    await user.click(closeButtons[0]!);
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  });

  it('Toast manager shows a toast', async () => {
    render(<Toaster />);
    act(() => {
      toast.add({ title: 'Deneme bildirimi', description: 'Deneme ayrinti' });
    });
    expect(await screen.findByText('Deneme bildirimi')).toBeInTheDocument();
  });
});
