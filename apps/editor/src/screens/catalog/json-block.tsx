import { prettyJson } from './readers';

/** A collapsed block with the JSON of an opaque field, shown as stored (indented only). */
export function JsonBlock({ title, value }: { title: string; value: unknown }) {
  return (
    <details className="rounded-lg border p-2">
      <summary className="min-h-6 cursor-pointer text-sm font-medium">{title}</summary>
      <pre className="mt-2 max-h-96 overflow-auto text-xs break-words whitespace-pre-wrap">
        {prettyJson(value)}
      </pre>
    </details>
  );
}
