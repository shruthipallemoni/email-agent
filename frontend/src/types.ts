// Mirrors the backend's Pydantic schemas (see backend/app/schemas/*.py).
// Keeping these in one place makes it easy to see exactly what shape of
// data the frontend expects from each endpoint.

export interface CurrentUser {
  email: string;
  name: string;
  picture: string | null;
}

export interface LoginStatus {
  authenticated: boolean;
  user: CurrentUser | null;
}

export interface EmailSummary {
  id: string;
  thread_id: string;
  subject: string;
  from_: string;
  date: string;
  snippet: string;
}

export interface EmailDetail {
  id: string;
  thread_id: string;
  subject: string;
  from_: string;
  to: string;
  date: string;
  snippet: string;
  body_text: string;
  body_html: string | null;
  message_id_header: string | null;
}

export interface EmailListResponse {
  emails: EmailSummary[];
  count: number;
}

export type Category =
  | "meeting"
  | "request"
  | "information"
  | "personal"
  | "spam"
  | "newsletter"
  | "other";

export type Level = "low" | "medium" | "high";

export interface EmailAnalysis {
  category: Category;
  intent: string;
  urgency: Level;
  risk_level: Level;
  requires_response: boolean;
  summary: string;
  reasoning: string;
}

export interface ReplyDraft {
  subject: string;
  body: string;
  notes: string;
}

export type ValidationSeverity = "none" | "low" | "medium" | "high";

export interface ReplyValidation {
  passed: boolean;
  issues: string[];
  severity: ValidationSeverity;
  reasoning: string;
}

export interface SentMessageInfo {
  gmail_message_id: string;
  thread_id: string;
}

export type AgentStatus = "completed" | "awaiting_approval";

export interface AgentRunResponse {
  status: AgentStatus;
  message_id: string;
  subject: string;
  sender: string;
  analysis: EmailAnalysis | null;
  action_decision: string | null;
  reply_draft: ReplyDraft | null;
  reply_validation: ReplyValidation | null;
  human_approval_required: boolean | null;
  sent: SentMessageInfo | null;
  log: string[];
}

export type PendingStatus = "awaiting_approval" | "completed" | "not_found";

export interface PendingApprovalResponse {
  status: PendingStatus;
  message_id: string;
  subject: string | null;
  sender: string | null;
  analysis: EmailAnalysis | null;
  reply_draft: ReplyDraft | null;
  reply_validation: ReplyValidation | null;
}

export interface ApprovalDecisionRequest {
  approved: boolean;
  edited_subject?: string | null;
  edited_body?: string | null;
}