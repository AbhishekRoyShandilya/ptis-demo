import { Link, useParams } from "react-router-dom";
import { Bar, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { inr, useData } from "../data";
import type { Bar as BarT, Scan } from "../types";
import { Loading, StatusChip, Title } from "../components/ui";

export default function StockPage() {
  const { symbol = "" } = useParams();
  const { data, error } = useData<{ symbol: string; bars: BarT[] }>(`series/${symbol}.json`);
  const { data: scan } = useData<Scan>("scan.json");
  if (!data) return <Loading error={error} />;
  const ev = scan?.evaluations.find((e) => e.symbol === symbol);
  const vmax = Math.max(...data.bars.map((b) => b.v));
  return (
    <div className="space-y-4">
      <Link to="/market" className="text-sm text-teal-700 hover:underline dark:text-teal-300">← Market</Link>
      <Title sub="Daily close with the strategy's 20- and 50-day EMAs, and volume. Last ~250 sessions, split/bonus adjusted.">{symbol}</Title>
      <div className="card h-[380px]">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data.bars} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeOpacity={0.15} />
            <XAxis dataKey="d" minTickGap={40} tick={{ fontSize: 11 }} />
            <YAxis yAxisId="p" domain={["auto", "auto"]} tick={{ fontSize: 11 }} width={60} />
            <YAxis yAxisId="v" orientation="right" hide domain={[0, vmax * 4]} />
            <Tooltip formatter={(v: number) => inr(v, 2)} />
            <Bar isAnimationActive={false} yAxisId="v" dataKey="v" name="Volume" fill="#94a3b8" fillOpacity={0.35} />
            <Line isAnimationActive={false} yAxisId="p" dataKey="c" name="Close" dot={false} stroke="#0f766e" strokeWidth={1.8} />
            <Line isAnimationActive={false} yAxisId="p" dataKey="e20" name="EMA 20" dot={false} stroke="#f59e0b" strokeWidth={1.2} />
            <Line isAnimationActive={false} yAxisId="p" dataKey="e50" name="EMA 50" dot={false} stroke="#6366f1" strokeWidth={1.2} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      {ev && (
        <div className="card">
          <div className="flex flex-wrap items-baseline gap-3">
            <h2 className="font-medium">Today's evaluation</h2>
            <span className="text-sm muted">score {ev.score.toFixed(2)} · regime {ev.regime.replace(/_/g, " ")}</span>
            {ev.valid ? <span className="chip bg-teal-100 text-teal-800 dark:bg-teal-900/50 dark:text-teal-200">valid signal</span>
                      : <span className="chip bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300">no signal</span>}
          </div>
          {ev.disqualified && (
            <p className="mt-2 text-sm">
              The engine stopped before checking conditions: <b>{ev.disqualification_reason}</b>. The template avoids
              that regime, so the stock is not a candidate today.
            </p>
          )}
          <ul className="mt-3 space-y-2">
            {ev.conditions.map((c) => (
              <li key={c.type} className="flex flex-wrap items-center gap-2 text-sm">
                <StatusChip status={c.status} category={c.category} />
                <span className="font-mono text-xs">{c.type}</span>
                <span className="muted">{c.category === "avoid" ? "(avoid)" : c.required ? "(required)" : "(supporting)"}</span>
                <span className="muted">{c.details}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
