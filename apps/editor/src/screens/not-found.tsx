import { PageHeading } from '@/components/page-heading';
import { tr } from '@/i18n/tr';

export function Component() {
  return (
    <div className="flex flex-col gap-2">
      <PageHeading>{tr.ui.notFoundTitle}</PageHeading>
      <p className="text-sm">{tr.ui.notFoundBody}</p>
    </div>
  );
}
