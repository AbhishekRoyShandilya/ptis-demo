import { useData } from "../data";
import type { StrategyDoc } from "../types";
import { Loading, Title } from "../components/ui";

const fmt = (p: Record<string, unknown>) =>
  Object.entries(p).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : String(v)}`).join(" · ");

export default function StrategyPage() {
  const { data: s, error } = useData<StrategyDoc>("strategy.json");
  if (!s) return <Loading error={error} />;
  return (
    <div className="space-y-4">
      <Title sub="The strategy taught to PTIS for this demo: a textbook daily EMA pullback, written as a PTIS strategy template. Illustrative only, not a recommendation.">
        {s.name}
      </Title>
      <div className="card text-sm">{s.description}</div>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="card">
          <h2 className="font-medium">Entry conditions</h2>
          <p className="mt-1 text-xs muted">Required conditions must all be met; supporting ones raise the score by their weight.</p>
          <ul className="mt-3 space-y-3">
            {s.confirmations.map((c) => (
              <li key={c.type} className="text-sm">
                <div className="flex items-center gap-2">
                  <span className={`chip ${c.required ? "bg-teal-100 text-teal-800 dark:bg-teal-900/50 dark:text-teal-200" : "bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300"}`}>
                    {c.required ? "required" : "supporting"}
                  </span>
                  <span className="font-medium">{c.description}</span>
                  <span className="ml-auto text-xs muted">weight {c.weight}</span>
                </div>
                <div className="mt-1 font-mono text-xs muted">{c.type} · {fmt(c.params)}</div>
              </li>
            ))}
          </ul>
          <h3 className="mt-5 font-medium">Avoid when</h3>
          <ul className="mt-2 space-y-2">
            {s.avoid_conditions.map((c) => (
              <li key={c.type} className="text-sm">
                {c.description}
                <div className="font-mono text-xs muted">{c.type} · {fmt(c.params)}</div>
              </li>
            ))}
          </ul>
        </div>
        <div className="space-y-4">
          <div className="card text-sm">
            <h2 className="font-medium">Regimes</h2>
            <p className="mt-2">Preferred: {s.regimes.preferred.join(", ").replace(/_/g, " ")}</p>
            <p>Avoided (disqualifies the stock): {s.regimes.avoid.join(", ").replace(/_/g, " ")}</p>
            <p className="mt-2 text-xs muted">
              Each stock's regime comes from the PTIS MarketRegimeDetector (ADX, slope, moving-average alignment, volatility).
            </p>
          </div>
          <div className="card text-sm">
            <h2 className="font-medium">Exits and risk</h2>
            <ul className="mt-2 list-disc space-y-1 pl-5">
              <li>Stop: {s.exit.stop.type} ({fmt(s.exit.stop.params)})</li>
              {s.exit.targets.map((t) => (
                <li key={t.r}>Take {t.size_pct}% at {t.r}R</li>
              ))}
              <li>Time exit after {s.exit.max_sessions} sessions</li>
              <li>Risk {s.risk.max_risk_pct}% of equity per trade, sized by the PTIS PositionSizer</li>
            </ul>
          </div>
        </div>
      </div>
      <details className="card">
        <summary className="cursor-pointer font-medium">The template exactly as PTIS reads it (YAML)</summary>
        <pre className="mt-3 overflow-x-auto rounded-lg bg-slate-100 p-3 text-xs dark:bg-slate-950">{s.yaml}</pre>
      </details>
    </div>
  );
}
