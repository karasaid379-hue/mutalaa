import { cn } from 'cn';
import { Loader2Icon } from 'lucide-react';

/** Decorative: the loading text is given by the caller (a single live region exists in the app). */
function Spinner({ className, ...props }: React.ComponentProps<'svg'>) {
  return (
    <Loader2Icon
      data-slot="spinner"
      aria-hidden="true"
      className={cn('size-4 animate-spin', className)}
      {...props}
    />
  );
}

export { Spinner };
