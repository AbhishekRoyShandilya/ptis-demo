import type { ReactNode } from "react";

export function Loading({ error }: { error?: string | null }) {
  return <div className="card muted">{error ? `Could not load data: ${error}` : "Loading…"}</div>;
}

export function Stat({ label, value, note }: { label: string; value: ReactNode; note?: ReactNode }) {
  return (
    <div className="card">
      <div className="text-xs uppercase tracking-wide muted">{label}</div>
      <div className="mt-1 text-xl font-semibold tabular-nums">{value}</div>
      {note && <div className="mt-1 text-xs muted">{note}</div>}
    </div>
  );
}

export function Title({ children, sub }: { children: ReactNode; sub?: ReactNode }) {
  return (
    <div className="mb-5">
      <h1 className="text-2xl font-semibold tracking-tight">{children}</h1>
      {sub && <p className="mt-1 max-w-3xl muted">{sub}</p>}
    </div>
  );
}

const STATUS: Record<string, string> = {
  met: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-200",
  not_met: "bg-rose-100 text-rose-800 dark:bg-rose-900/50 dark:text-rose-200",
  partially_met: "bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-200",
  inconclusive: "bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  error: "bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
};

export function StatusChip({ status, category }: { status: string; category?: string }) {
  // for an AVOID condition, "met" means the bad thing happened: show it as triggered (red), "not met" as clear (green)
  if (category === "avoid" && (status === "met" || status === "not_met")) {
    const triggered = status === "met";
    return <span className={`chip ${STATUS[triggered ? "not_met" : "met"]}`}>{triggered ? "triggered" : "clear"}</span>;
  }
  return <span className={`chip ${STATUS[status] ?? STATUS.inconclusive}`}>{status.replace("_", " ")}</span>;
}

export function Sparkline({ values, up }: { values: number[]; up: boolean }) {
  const v = values.filter((x) => x !== null);
  if (v.length < 2) return null;
  const min = Math.min(...v), max = Math.max(...v), w = 96, h = 26;
  const pts = v.map((x, i) => `${(i / (v.length - 1)) * w},${h - ((x - min) / (max - min || 1)) * h}`).join(" ");
  return (
    <svg width={w} height={h} className="overflow-visible" aria-hidden>
      <polyline points={pts} fill="none" strokeWidth="1.5" className={up ? "stroke-emerald-600" : "stroke-rose-600"} />
    </svg>
  );
}
