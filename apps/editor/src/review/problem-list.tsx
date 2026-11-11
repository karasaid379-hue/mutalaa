import { focusField, problemId, type FieldProblem } from './field-errors';

/** A message that links to its field (plain text when it has none). */
export function ProblemLink({ problem }: { problem: FieldProblem }) {
  const { fieldId, message } = problem;
  if (fieldId === null) return <>{message}</>;
  return (
    <a
      href={`#${fieldId}`}
      className="underline"
      onClick={(event) => {
        event.preventDefault();
        focusField(fieldId);
      }}
    >
      {message}
    </a>
  );
}

/** The messages of an error summary; every item has the id the field points to. */
export function ProblemList({
  problems,
  listId,
}: {
  problems: readonly FieldProblem[];
  listId: string;
}) {
  return (
    <ul className="list-disc pl-5">
      {problems.map((problem, index) => (
        <li key={`${index}:${problem.message}`} id={problemId(listId, index)}>
          <ProblemLink problem={problem} />
        </li>
      ))}
    </ul>
  );
}
