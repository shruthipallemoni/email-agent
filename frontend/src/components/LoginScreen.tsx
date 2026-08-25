export function LoginScreen({ loginUrl }: { loginUrl: string }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-paper px-4">
      <div className="w-full max-w-sm text-center">
        <h1 className="font-display text-4xl font-semibold tracking-tight">Relay</h1>
        <p className="mt-2 text-ink/60">
          Reads your inbox, drafts replies, and waits for your OK before anything goes out.
        </p>
        <a
          href={loginUrl}
          className="mt-8 inline-flex items-center justify-center rounded-md bg-ink px-5 py-2.5 text-sm font-medium text-paper hover:bg-ink/90"
        >
          Continue with Google
        </a>
      </div>
    </div>
  );
}