import type { EmailSummary } from "../types";

export function EmailList({
  emails,
  selectedId,
  onSelect,
  loading,
}: {
  emails: EmailSummary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  loading: boolean;
}) {
  if (loading) {
    return <div className="p-6 text-sm text-ink/50">Loading your inbox…</div>;
  }

  if (emails.length === 0) {
    return (
      <div className="p-6 text-sm text-ink/50">
        Nothing here. New mail will show up once it arrives.
      </div>
    );
  }

  return (
    <ul className="divide-y divide-ink/10">
      {emails.map((email) => {
        const isSelected = email.id === selectedId;
        return (
          <li key={email.id}>
            <button
              onClick={() => onSelect(email.id)}
              className={`block w-full px-4 py-3 text-left transition-colors ${
                isSelected ? "bg-slate" : "hover:bg-slate/50"
              }`}
            >
              <div className="flex items-baseline justify-between gap-2">
                <span className="truncate text-sm font-medium text-ink">
                  {email.from_.replace(/<.*>/, "").trim() || email.from_}
                </span>
                <span className="shrink-0 text-xs text-ink/40">{formatDate(email.date)}</span>
              </div>
              <p className="mt-0.5 truncate text-sm text-ink/80">{email.subject}</p>
              <p className="mt-0.5 truncate text-xs text-ink/45">{email.snippet}</p>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

function formatDate(raw: string): string {
  const d = new Date(raw);
  if (isNaN(d.getTime())) return "";
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}