type Tone = "success" | "warning" | "danger" | "info" | "neutral";

const TONE_STYLES: Record<Tone, string> = {
  success: "bg-moss/10 text-moss border-moss/30",
  warning: "bg-signal/10 text-signal border-signal/30",
  danger: "bg-rust/10 text-rust border-rust/30",
  info: "bg-mist/10 text-mist border-mist/30",
  neutral: "bg-slate text-ink/60 border-ink/10",
};

export function StatusChip({ label, tone }: { label: string; tone: Tone }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium tracking-wide ${TONE_STYLES[tone]}`}
    >
      {label}
    </span>
  );
}

// Small helpers so callers don't need to memorize which tone maps to which
// urgency/risk word - one place to change if the mapping ever needs to change.
export function urgencyTone(level: "low" | "medium" | "high"): Tone {
  return level === "high" ? "danger" : level === "medium" ? "warning" : "info";
}

export function riskTone(level: "low" | "medium" | "high"): Tone {
  return level === "high" ? "danger" : level === "medium" ? "warning" : "success";
}