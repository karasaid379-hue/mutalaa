import { BookOpenCheckIcon, UserCheckIcon } from 'lucide-react';
import { useId } from 'react';
import { Badge } from '@/components/ui/badge';
import { trLemma } from '@/i18n/tr-lemma';
import type { ApprovalPath } from './approval';

/**
 * The approval path of a Turkish lemma mapping. "Sözlük kanıtıyla otomatik" is a dashed outline with its own
 * icon: it is never drawn like the editor approval and never like the unverified badge (K-25), and the meaning
 * is in the text, not in the colour. Its explanation is hidden text tied with `aria-describedby`.
 */
export function ApprovalBadge({ path }: { path: ApprovalPath }) {
  const hintId = useId();
  if (path === 'otomatik') {
    return (
      <>
        <Badge
          variant="outline"
          className="border-dashed"
          aria-describedby={hintId}
          data-testid="approval-badge"
          data-approval-path="otomatik"
        >
          <BookOpenCheckIcon aria-hidden="true" />
          {trLemma.approval.otomatik}
        </Badge>
        <span id={hintId} className="sr-only">
          {trLemma.approval.otomatikHint}
        </span>
      </>
    );
  }
  return (
    <>
      <Badge
        variant="secondary"
        aria-describedby={hintId}
        data-testid="approval-badge"
        data-approval-path="editor"
      >
        <UserCheckIcon aria-hidden="true" />
        {trLemma.approval.editor}
      </Badge>
      <span id={hintId} className="sr-only">
        {trLemma.approval.editorHint}
      </span>
    </>
  );
}
