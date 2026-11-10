import { Link } from 'react-router';
import { PageHeading } from '@/components/page-heading';
import { tr } from '@/i18n/tr';

/**
 * `/yetki-yok`: the signed-in user has no role. There is deliberately no logout button: a user
 * without a role cannot call `logout` either (Backend API 4); the page only offers a retry.
 */
export function Component() {
  return (
    <main className="mx-auto flex max-w-md flex-col gap-4 p-6">
      <PageHeading>{tr.session.forbiddenTitle}</PageHeading>
      <p className="text-sm">{tr.session.forbiddenBody}</p>
      <Link to="/" className="underline">
        {tr.session.forbiddenRetry}
      </Link>
    </main>
  );
}
