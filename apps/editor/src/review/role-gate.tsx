import { useId, type ReactNode } from 'react';
import { useApi } from '@/app/api-context';
import { tr } from '@/i18n/tr';
import { canLemmaAction } from '@/lib/roles';
import { ME_PATH, SESSION_QUERY_OPTIONS } from './queries';

export interface EditorActionGateProps {
  /** Heading of the action; shown above the note when the role is missing. */
  heading: string;
  testId: string;
  children: ReactNode;
}

/**
 * Shows an action only to the roles the server lets use it (Editor policy: editor and admin; the expert role gets a
 * 403 there). The expert sees the heading and "Bu eylem editör rolü ister". While the session is unknown nothing is
 * shown (like the link actions). The server has the last word.
 */
export function EditorActionGate({ heading, testId, children }: EditorActionGateProps) {
  const api = useApi();
  const headingId = useId();
  const me = api.$api.useQuery('get', ME_PATH, undefined, SESSION_QUERY_OPTIONS);
  if (me.data === undefined) return null;
  if (canLemmaAction(me.data.roller)) return <>{children}</>;
  return (
    <section
      aria-labelledby={headingId}
      className="flex flex-col gap-1 rounded-lg border p-3"
      data-testid={`${testId}-role-note`}
    >
      <h3 id={headingId} className="text-sm font-medium">
        {heading}
      </h3>
      <p className="text-sm text-muted-foreground">{tr.review.editorActionNote}</p>
    </section>
  );
}
