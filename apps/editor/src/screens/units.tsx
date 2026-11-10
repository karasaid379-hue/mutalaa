import { PageHeading } from '@/components/page-heading';
import { tr } from '@/i18n/tr';

// Placeholder of A15.3: the units screen is written in A15.5.
export function Component() {
  return <PageHeading>{tr.nav.units}</PageHeading>;
}
