import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { TextDiff } from '@/components/text-diff';
import { reviewFieldLabel } from '@/i18n/labels';
import { tr } from '@/i18n/tr';
import { describeChanges } from './stale';
import type { ReviewDetail } from './types';

/**
 * Shown after a 412: what changed between the record the editor was looking at and the fresh one.
 * The editor's own input is kept by the form; nothing is resent automatically.
 */
export function StaleRecord({ before, after }: { before: ReviewDetail; after: ReviewDetail }) {
  const changes = describeChanges(before, after);
  return (
    <Alert data-testid="stale-record">
      <AlertTitle>{tr.review.stale.title}</AlertTitle>
      <AlertDescription className="flex flex-col gap-2">
        <p>{tr.review.stale.body}</p>
        {after.durum !== 'acik' ? <p>{tr.review.stale.closedNow}</p> : null}
        {changes.length === 0 ? (
          <p>{tr.review.stale.noFieldChange}</p>
        ) : (
          <table className="w-full text-left text-sm">
            <caption className="text-left font-medium">{tr.review.stale.fieldsHeading}</caption>
            <thead>
              <tr>
                <th scope="col">{tr.review.stale.field}</th>
                <th scope="col">{tr.review.stale.before}</th>
                <th scope="col">{tr.review.stale.after}</th>
              </tr>
            </thead>
            <tbody>
              {changes.map((change) => (
                <tr key={change.field} className="align-top">
                  <th scope="row" className="pr-2 font-medium">
                    {reviewFieldLabel(change.field)}
                  </th>
                  <td className="pr-2">{change.before}</td>
                  <td>{change.after}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {changes
          .filter((change) => change.text)
          .map((change) => (
            <div key={change.field}>
              <p className="font-medium">{`${tr.review.stale.textHeading}: ${reviewFieldLabel(change.field)}`}</p>
              <TextDiff before={change.text!.before} after={change.text!.after} />
              <p className="text-xs text-muted-foreground">{tr.review.diff.legend}</p>
            </div>
          ))}
      </AlertDescription>
    </Alert>
  );
}
