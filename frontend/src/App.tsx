import { useEffect, useState } from "react";
import { api, ApiError } from "./api/client";
import { EmailDetailPanel } from "./components/EmailDetailPanel";
import { EmailList } from "./components/EmailList";
import { Header } from "./components/Header";
import { LoginScreen } from "./components/LoginScreen";
import type { CurrentUser, EmailSummary } from "./types";

type AuthPhase = "checking" | "signed_out" | "signed_in";

function App() {
  const [authPhase, setAuthPhase] = useState<AuthPhase>("checking");
  const [user, setUser] = useState<CurrentUser | null>(null);

  const [emails, setEmails] = useState<EmailSummary[]>([]);
  const [emailsLoading, setEmailsLoading] = useState(false);
  const [emailsError, setEmailsError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // On mobile, selecting an email pushes to a detail view; this tracks that.
  const [mobileShowDetail, setMobileShowDetail] = useState(false);

  useEffect(() => {
    api
      .getMe()
      .then((status) => {
        if (status.authenticated && status.user) {
          setUser(status.user);
          setAuthPhase("signed_in");
        } else {
          setAuthPhase("signed_out");
        }
      })
      .catch(() => setAuthPhase("signed_out"));
  }, []);

  useEffect(() => {
    if (authPhase !== "signed_in") return;

    setEmailsLoading(true);
    api
      .listEmails()
      .then((res) => setEmails(res.emails))
      .catch((err) => setEmailsError(err instanceof ApiError ? err.message : "Couldn't load your inbox."))
      .finally(() => setEmailsLoading(false));
  }, [authPhase]);

  async function handleLogout() {
    await api.logout();
    setUser(null);
    setAuthPhase("signed_out");
  }

  function handleSelect(id: string) {
    setSelectedId(id);
    setMobileShowDetail(true);
  }

  if (authPhase === "checking") {
    return <div className="flex min-h-screen items-center justify-center text-sm text-ink/40">Loading…</div>;
  }

  if (authPhase === "signed_out" || !user) {
    return <LoginScreen loginUrl={api.loginUrl()} />;
  }

  return (
    <div className="flex h-screen flex-col">
      <Header user={user} onLogout={handleLogout} />

      <div className="flex min-h-0 flex-1">
        {/* Inbox list - hidden on mobile once a detail view is open */}
        <div
          className={`w-full shrink-0 overflow-y-auto border-r border-ink/10 sm:block sm:w-80 ${
            mobileShowDetail ? "hidden" : "block"
          }`}
        >
          {emailsError ? (
            <div className="p-6 text-sm text-rust">{emailsError}</div>
          ) : (
            <EmailList
              emails={emails}
              selectedId={selectedId}
              onSelect={handleSelect}
              loading={emailsLoading}
            />
          )}
        </div>

        {/* Detail panel */}
        <div className={`min-h-0 flex-1 overflow-y-auto ${mobileShowDetail ? "block" : "hidden"} sm:block`}>
          {selectedId ? (
            <>
              <button
                onClick={() => setMobileShowDetail(false)}
                className="m-4 text-sm text-ink/50 hover:text-ink sm:hidden"
              >
                ← Back to inbox
              </button>
              <EmailDetailPanel key={selectedId} emailId={selectedId} />
            </>
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-ink/40">
              Select an email to get started.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;