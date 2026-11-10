import { useRouteError } from 'react-router';
import { PageHeading } from '@/components/page-heading';
import { ProblemMessage } from '@/components/problem-message';
import { tr } from '@/i18n/tr';

/** Error boundary of the routes: a thrown problem (network failure while checking the session, a bug) is shown, not a blank page. */
export function RouteError() {
  const error = useRouteError();
  return (
    <main className="mx-auto flex max-w-xl flex-col gap-4 p-6">
      <PageHeading>{tr.ui.errorTitle}</PageHeading>
      <ProblemMessage error={error} />
    </main>
  );
}
