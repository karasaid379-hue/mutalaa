import { cn } from 'cn';
import { Loader2Icon } from 'lucide-react';
import { tr } from '@/i18n/tr';

function Spinner({ className, ...props }: React.ComponentProps<'svg'>) {
  return (
    <Loader2Icon
      data-slot="spinner"
      role="status"
      aria-label={tr.ui.loading}
      className={cn('size-4 animate-spin', className)}
      {...props}
    />
  );
}

export { Spinner };
