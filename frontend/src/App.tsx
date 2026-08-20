import { useEffect, useState } from "react";

// This is a very simple first page - just enough to prove login and Gmail
// reading both work. The real dashboard gets built in Block 11.

const API_BASE = "http://localhost:8000/api";

type HealthResponse = {
  status: string;
  app_name: string;
  environment: string;
};

type CurrentUser = {
  email: string;
  name: string;
  picture: string | null;
};

type LoginStatus = {
  authenticated: boolean;
  user: CurrentUser | null;
};

type EmailSummary = {
  id: string;
  thread_id: string;
  subject: string;
  from_: string;
  date: string;
  snippet: string;
};

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [authStatus, setAuthStatus] = useState<LoginStatus | null>(null);

  const [emails, setEmails] = useState<EmailSummary[] | null>(null);
  const [emailsLoading, setEmailsLoading] = useState(false);
  const [emailsError, setEmailsError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((res) => res.json())
      .then((data) => setHealth(data))
      .catch(() => setError("Could not reach the backend. Is it running?"));

    // "credentials: include" is required so the browser sends our login
    // cookie along with this request.
    fetch(`${API_BASE}/auth/me`, { credentials: "include" })
      .then((res) => res.json())
      .then((data) => setAuthStatus(data))
      .catch(() => setAuthStatus({ authenticated: false, user: null }));
  }, []);

  const handleLogin = () => {
    window.location.href = `${API_BASE}/auth/login`;
  };

  const handleLogout = async () => {
    await fetch(`${API_BASE}/auth/logout`, { method: "POST", credentials: "include" });
    setAuthStatus({ authenticated: false, user: null });
    setEmails(null);
  };

  const loadEmails = async () => {
    setEmailsLoading(true);
    setEmailsError(null);
    try {
      const res = await fetch(`${API_BASE}/emails?max_results=10`, { credentials: "include" });
      if (!res.ok) {
        throw new Error(`Server responded with ${res.status}`);
      }
      const data = await res.json();
      setEmails(data.emails);
    } catch (err) {
      setEmailsError("Could not load emails. Try logging in again.");
    } finally {
      setEmailsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-start justify-center bg-gray-50 py-10">
      <div className="bg-white shadow-md rounded-lg p-8 max-w-xl w-full">
        <h1 className="text-2xl font-semibold text-gray-800 mb-4 text-center">
          AI Email & Productivity Agent
        </h1>

        {health && (
          <p className="text-green-600 mb-4 text-center">
            ✅ Connected to backend ({health.app_name} - {health.environment})
          </p>
        )}
        {error && <p className="text-red-600 mb-4 text-center">❌ {error}</p>}

        <div className="text-center mb-6">
          {authStatus?.authenticated && authStatus.user ? (
            <div>
              <p className="text-gray-700 mb-2">
                Logged in as <span className="font-medium">{authStatus.user.name}</span> (
                {authStatus.user.email})
              </p>
              <div className="flex gap-2 justify-center">
                <button
                  onClick={loadEmails}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  {emailsLoading ? "Loading..." : "Load recent emails"}
                </button>
                <button
                  onClick={handleLogout}
                  className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
                >
                  Log out
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={handleLogin}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Log in with Google
            </button>
          )}
        </div>

        {emailsError && <p className="text-red-600 text-center mb-4">❌ {emailsError}</p>}

        {emails && (
          <ul className="divide-y divide-gray-200 border rounded">
            {emails.map((email) => (
              <li key={email.id} className="p-3">
                <p className="font-medium text-gray-800">{email.subject}</p>
                <p className="text-sm text-gray-500">
                  {email.from_} — {email.date}
                </p>
                <p className="text-sm text-gray-600 mt-1">{email.snippet}</p>
              </li>
            ))}
            {emails.length === 0 && (
              <li className="p-3 text-gray-500 text-center">No emails found.</li>
            )}
          </ul>
        )}
      </div>
    </div>
  );
}

export default App;