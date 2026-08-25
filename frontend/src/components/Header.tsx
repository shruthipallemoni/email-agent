import type { CurrentUser } from "../types";

export function Header({ user, onLogout }: { user: CurrentUser; onLogout: () => void }) {
  return (
    <header className="flex items-center justify-between border-b border-ink/10 bg-paper px-6 py-4">
      <div className="flex items-baseline gap-2">
        <h1 className="font-display text-2xl font-semibold tracking-tight">Relay</h1>
        <span className="hidden text-sm text-ink/50 sm:inline">AI email agent</span>
      </div>

      <div className="flex items-center gap-3">
        {user.picture ? (
          <img src={user.picture} alt="" className="h-7 w-7 rounded-full" />
        ) : (
          <div className="h-7 w-7 rounded-full bg-slate" />
        )}
        <span className="hidden text-sm text-ink/70 sm:inline">{user.name}</span>
        <button
          onClick={onLogout}
          className="rounded-md border border-ink/15 px-3 py-1.5 text-sm text-ink/70 hover:bg-slate"
        >
          Log out
        </button>
      </div>
    </header>
  );
}