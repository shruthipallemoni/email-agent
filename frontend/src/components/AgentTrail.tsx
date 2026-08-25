// Shows exactly what the agent did, in order, like tracking a parcel's
// journey. The order is real information here (each step happened after
// the one before it), which is what earns this a numbered timeline rather
// than a plain bullet list.

export function AgentTrail({ steps }: { steps: string[] }) {
  if (steps.length === 0) return null;

  return (
    <ol className="relative border-l border-ink/15 pl-6">
      {steps.map((step, i) => (
        <li key={i} className="mb-4 last:mb-0">
          <span className="absolute -left-[9px] flex h-4 w-4 items-center justify-center rounded-full border-2 border-paper bg-ink/70 text-[9px] font-mono text-paper">
            {i + 1}
          </span>
          <p className="font-mono text-xs leading-relaxed text-ink/70">{step}</p>
        </li>
      ))}
    </ol>
  );
}