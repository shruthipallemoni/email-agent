import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { EmailAnalysis, EmailDetail, ReplyDraft, ReplyValidation, SentMessageInfo } from "../types";
import { AgentTrail } from "./AgentTrail";
import { riskTone, StatusChip, urgencyTone } from "./StatusChip";

type Phase = "loading" | "idle" | "running" | "awaiting_approval" | "completed" | "error";

export function EmailDetailPanel({ emailId }: { emailId: string }) {
  const [phase, setPhase] = useState<Phase>("loading");
  const [email, setEmail] = useState<EmailDetail | null>(null);
  const [analysis, setAnalysis] = useState<EmailAnalysis | null>(null);
  const [draft, setDraft] = useState<ReplyDraft | null>(null);
  const [validation, setValidation] = useState<ReplyValidation | null>(null);
  const [trail, setTrail] = useState<string[]>([]);
  const [sent, setSent] = useState<SentMessageInfo | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [subjectDraft, setSubjectDraft] = useState("");
  const [bodyDraft, setBodyDraft] = useState("");
  const [deciding, setDeciding] = useState(false);

  // Whenever a different email is selected, load its content and check
  // whether the agent has already run on it (so the review view survives
  // switching away and back, since the backend remembers via Block 9's
  // checkpointer).
  useEffect(() => {
    let cancelled = false;

    async function load() {
      setPhase("loading");
      setErrorMessage(null);
      setAnalysis(null);
      setDraft(null);
      setValidation(null);
      setTrail([]);
      setSent(null);

      try {
        const [emailDetail, pending] = await Promise.all([
          api.getEmail(emailId),
          api.getPendingApproval(emailId),
        ]);
        if (cancelled) return;

        setEmail(emailDetail);

        if (pending.status === "awaiting_approval" && pending.reply_draft) {
          setAnalysis(pending.analysis);
          setDraft(pending.reply_draft);
          setValidation(pending.reply_validation);
          setSubjectDraft(pending.reply_draft.subject);
          setBodyDraft(pending.reply_draft.body);
          setPhase("awaiting_approval");
        } else if (pending.status === "completed") {
          setAnalysis(pending.analysis);
          setDraft(pending.reply_draft);
          setValidation(pending.reply_validation);
          setPhase("completed");
        } else {
          setPhase("idle");
        }
      } catch (err) {
        if (!cancelled) {
          setErrorMessage(err instanceof ApiError ? err.message : "Couldn't load this email.");
          setPhase("error");
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [emailId]);

  async function handleRunAgent() {
    setPhase("running");
    setErrorMessage(null);
    try {
      const result = await api.runAgent(emailId);
      setAnalysis(result.analysis);
      setTrail(result.log);

      if (result.status === "awaiting_approval" && result.reply_draft) {
        setDraft(result.reply_draft);
        setValidation(result.reply_validation);
        setSubjectDraft(result.reply_draft.subject);
        setBodyDraft(result.reply_draft.body);
        setPhase("awaiting_approval");
      } else {
        setPhase("completed");
      }
    } catch (err) {
      setErrorMessage(err instanceof ApiError ? err.message : "The agent hit a problem.");
      setPhase("error");
    }
  }

  async function handleDecision(approved: boolean) {
    if (!draft) return;
    setDeciding(true);
    setErrorMessage(null);
    try {
      const edited = subjectDraft !== draft.subject || bodyDraft !== draft.body;
      const result = await api.approve(emailId, {
        approved,
        edited_subject: edited ? subjectDraft : null,
        edited_body: edited ? bodyDraft : null,
      });
      setDraft(result.reply_draft);
      setValidation(result.reply_validation);
      setSent(result.sent);
      setTrail((prev) => [...prev, ...result.log]);
      setPhase("completed");
    } catch (err) {
      setErrorMessage(err instanceof ApiError ? err.message : "Couldn't submit your decision.");
    } finally {
      setDeciding(false);
    }
  }

  if (phase === "loading") {
    return <Centered>Loading…</Centered>;
  }
  if (!email) {
    return <Centered>Couldn't find that email.</Centered>;
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-8">
      {/* Original email */}
      <div className="border-b border-ink/10 pb-6">
        <h2 className="font-display text-2xl font-semibold leading-snug">{email.subject}</h2>
        <p className="mt-1 text-sm text-ink/60">
          From <span className="text-ink/80">{email.from_}</span> · {email.date}
        </p>
        {/* Safe to render directly: the backend sanitizes this HTML with
            nh3 before it ever reaches here (see _sanitize_email_html in
            gmail_service.py) - scripts, event handlers, and iframes are
            stripped server-side. Never render body_html from anywhere
            else without the same sanitization. */}
        {email.body_html ? (
          <div
            className="email-body mt-4 text-sm leading-relaxed text-ink/80"
            dangerouslySetInnerHTML={{ __html: email.body_html }}
          />
        ) : (
          <p className="mt-4 whitespace-pre-wrap text-sm leading-relaxed text-ink/80">
            {email.body_text || email.snippet}
          </p>
        )}
      </div>

      {errorMessage && (
        <div className="mt-6 rounded-md border border-rust/30 bg-rust/5 px-4 py-3 text-sm text-rust">
          {errorMessage}
        </div>
      )}

      {/* Idle: nothing run yet */}
      {(phase === "idle" || (phase === "error" && !analysis)) && (
        <div className="mt-6">
          <button
            onClick={handleRunAgent}
            className="rounded-md bg-ink px-4 py-2 text-sm font-medium text-paper hover:bg-ink/90"
          >
            Run agent
          </button>
        </div>
      )}

      {phase === "running" && (
        <div className="mt-6 text-sm text-ink/50">Reading, analyzing, drafting…</div>
      )}

      {/* Analysis */}
      {analysis && (
        <div className="mt-6 space-y-3">
          <div className="flex flex-wrap gap-2">
            <StatusChip label={analysis.category} tone="neutral" />
            <StatusChip label={`${analysis.urgency} urgency`} tone={urgencyTone(analysis.urgency)} />
            <StatusChip label={`${analysis.risk_level} risk`} tone={riskTone(analysis.risk_level)} />
          </div>
          <p className="text-sm text-ink/70">{analysis.summary}</p>
        </div>
      )}

      {/* Draft + validation + decision controls */}
      {draft && phase === "awaiting_approval" && (
        <div className="mt-6 rounded-lg border border-signal/30 bg-signal/5 p-4">
          <div className="mb-3 flex items-center justify-between">
            <span className="font-mono text-xs uppercase tracking-wide text-signal">
              Awaiting your approval
            </span>
            {validation && (
              <StatusChip
                label={validation.passed ? "Passed checks" : `Flagged: ${validation.severity}`}
                tone={validation.passed ? "success" : "danger"}
              />
            )}
          </div>

          {validation && validation.issues.length > 0 && (
            <ul className="mb-3 list-inside list-disc space-y-0.5 text-xs text-rust">
              {validation.issues.map((issue, i) => (
                <li key={i}>{issue}</li>
              ))}
            </ul>
          )}

          <label className="mb-1 block text-xs font-medium text-ink/60">Subject</label>
          <input
            value={subjectDraft}
            onChange={(e) => setSubjectDraft(e.target.value)}
            className="mb-3 w-full rounded-md border border-ink/15 bg-paper px-3 py-2 text-sm"
          />

          <label className="mb-1 block text-xs font-medium text-ink/60">Reply</label>
          <textarea
            value={bodyDraft}
            onChange={(e) => setBodyDraft(e.target.value)}
            rows={7}
            className="mb-1 w-full rounded-md border border-ink/15 bg-paper px-3 py-2 text-sm leading-relaxed"
          />
          {draft.notes && <p className="mb-3 text-xs italic text-ink/45">Agent's note: {draft.notes}</p>}

          <div className="flex gap-2">
            <button
              onClick={() => handleDecision(true)}
              disabled={deciding}
              className="rounded-md bg-moss px-4 py-2 text-sm font-medium text-paper hover:bg-moss/90 disabled:opacity-50"
            >
              {deciding ? "Sending…" : "Approve & send"}
            </button>
            <button
              onClick={() => handleDecision(false)}
              disabled={deciding}
              className="rounded-md border border-ink/15 px-4 py-2 text-sm text-ink/70 hover:bg-slate disabled:opacity-50"
            >
              Reject
            </button>
          </div>
        </div>
      )}

      {/* Completed */}
      {phase === "completed" && (
        <div className="mt-6 rounded-lg border border-moss/30 bg-moss/5 p-4">
          {sent ? (
            <p className="text-sm text-moss">
              Sent via Gmail <span className="font-mono text-xs">({sent.gmail_message_id})</span>
            </p>
          ) : draft ? (
            <p className="text-sm text-ink/60">This draft was reviewed and not sent.</p>
          ) : (
            <p className="text-sm text-ink/60">No reply was needed for this email.</p>
          )}
        </div>
      )}

      {/* Agent trail */}
      {trail.length > 0 && (
        <div className="mt-8">
          <h3 className="mb-3 font-mono text-xs uppercase tracking-wide text-ink/40">Agent trail</h3>
          <AgentTrail steps={trail} />
        </div>
      )}
    </div>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return <div className="flex h-full items-center justify-center text-sm text-ink/40">{children}</div>;
}