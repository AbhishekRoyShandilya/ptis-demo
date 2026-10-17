import { useState } from "react";
import { Area, AreaChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { inr, pct, useData } from "../data";
import type { Paper } from "../types";
import { Loading, Stat, Title } from "../components/ui";

const n = (v: number | string | null | undefined) => (typeof v === "number" ? v : Number(v ?? NaN));

export default function PaperPage() {
  const { data: p, error } = useData<Paper>("paper.json");
  const [showAll, setShowAll] = useState(false);
  if (!p) return <Loading error={error} />;
  const s = p.stats;
  const trades = [...p.closed].reverse();
  const shown = showAll ? trades : trades.slice(0, 20);
  return (
    <div className="space-y-5">
      <Title sub={<>The PTIS engine trades the demo strategy on paper from {p.rules.paper_start} with ₹{inr(p.rules.capital)} of virtual capital and at most {p.rules.max_positions} positions. Signals on the close, entries at the next open, delivery costs included. The numbers are what they are: this is a textbook strategy, shown honestly.</>}>
        Paper trader
      </Title>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Return" value={pct(n(s.return_pct))} note={`equal-weight NIFTY 50 hold: ${pct(n(s.benchmark_equal_weight_return_pct))}`} />
        <Stat label="Max drawdown" value={pct(n(s.max_drawdown_pct))} note={`${s.start} → ${s.end}`} />
        <Stat label="Closed trades" value={s.trades ?? 0} note={`${s.open_positions} open now`} />
        <Stat label="Win rate" value={s.win_rate_pct != null ? `${n(s.win_rate_pct).toFixed(1)}%` : "—"} note={`avg ${n(s.avg_r).toFixed(2)}R · median ${n(s.median_r).toFixed(2)}R`} />
      </div>

      <div className="card text-sm">
        <b>Read these numbers with their weaknesses.</b> {s.trades} trades in under a year is a small sample; the median
        trade ({n(s.median_r).toFixed(2)}R) says more than the average; the top 3 winners made {n(s.top3_share_of_gross_profit_pct).toFixed(0)}% of the gross
        profit. The universe is today's NIFTY 50 (survivorship-biased), and dividends are not added back, so an
        ex-dividend gap counts as a price loss here. This page shows the engine working, not an edge.
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="card h-72 md:col-span-2">
          <div className="mb-2 text-sm font-medium">Equity (₹)</div>
          <ResponsiveContainer width="100%" height="88%">
            <LineChart data={p.equity_curve} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeOpacity={0.15} />
              <XAxis dataKey="date" minTickGap={50} tick={{ fontSize: 11 }} />
              <YAxis domain={["auto", "auto"]} tick={{ fontSize: 11 }} width={70} tickFormatter={(v) => inr(v)} />
              <Tooltip formatter={(v: number) => `₹${inr(v)}`} />
              <Line isAnimationActive={false} dataKey="equity" dot={false} stroke="#0f766e" strokeWidth={1.8} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="card h-72">
          <div className="mb-2 text-sm font-medium">Drawdown (%)</div>
          <ResponsiveContainer width="100%" height="88%">
            <AreaChart data={p.equity_curve} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <XAxis dataKey="date" hide />
              <YAxis tick={{ fontSize: 11 }} width={40} />
              <Tooltip formatter={(v: number) => `${v.toFixed(2)}%`} />
              <Area isAnimationActive={false} dataKey="drawdown_pct" stroke="#e11d48" fill="#e11d48" fillOpacity={0.15} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <section>
        <h2 className="mb-2 font-medium">Open positions</h2>
        <div className="card overflow-x-auto p-0">
          <table className="w-full min-w-[720px]">
            <thead className="border-b border-slate-200 dark:border-slate-800"><tr>
              <th className="th">Symbol</th><th className="th">Since</th><th className="th num">Qty</th><th className="th num">Entry</th>
              <th className="th num">Stop</th><th className="th num">1.5R</th><th className="th num">3R</th><th className="th num">Last</th><th className="th num">Unrealised</th>
            </tr></thead>
            <tbody>
              {p.open.length === 0 && <tr><td className="td muted" colSpan={9}>No open positions.</td></tr>}
              {p.open.map((o) => (
                <tr key={o.symbol} className="border-b border-slate-100 last:border-0 dark:border-slate-800/60">
                  <td className="td font-medium">{o.symbol}</td><td className="td">{o.entry_date}</td>
                  <td className="td num">{o.qty_left}/{o.qty}</td><td className="td num">{inr(o.entry, 2)}</td>
                  <td className="td num">{inr(o.stop, 2)}</td><td className="td num">{inr(o.t1, 2)}</td><td className="td num">{inr(o.t2, 2)}</td>
                  <td className="td num">{inr(o.last, 2)}</td>
                  <td className={`td num ${o.unrealised >= 0 ? "text-emerald-700 dark:text-emerald-400" : "text-rose-700 dark:text-rose-400"}`}>₹{inr(o.unrealised)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="mb-2 font-medium">Closed trades (newest first)</h2>
        <div className="card overflow-x-auto p-0">
          <table className="w-full min-w-[820px]">
            <thead className="border-b border-slate-200 dark:border-slate-800"><tr>
              <th className="th">Symbol</th><th className="th">Entry</th><th className="th">Exit</th><th className="th num">Days</th>
              <th className="th num">Entry ₹</th><th className="th num">Stop ₹</th><th className="th">How it ended</th><th className="th num">R</th><th className="th num">P&amp;L ₹</th>
            </tr></thead>
            <tbody>
              {shown.map((t, i) => (
                <tr key={`${t.symbol}-${t.entry_date}-${i}`} className="border-b border-slate-100 last:border-0 dark:border-slate-800/60">
                  <td className="td font-medium">{t.symbol}</td><td className="td">{t.entry_date}</td><td className="td">{t.exit_date}</td>
                  <td className="td num">{t.sessions}</td><td className="td num">{inr(t.entry, 2)}</td><td className="td num">{inr(t.stop, 2)}</td>
                  <td className="td text-xs">{t.fills.map((f) => f.reason).join(" → ")}</td>
                  <td className={`td num ${t.r >= 0 ? "text-emerald-700 dark:text-emerald-400" : "text-rose-700 dark:text-rose-400"}`}>{t.r.toFixed(2)}</td>
                  <td className="td num">{inr(t.pnl)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!showAll && trades.length > 20 && (
          <button className="mt-2 text-sm text-teal-700 underline dark:text-teal-300" onClick={() => setShowAll(true)}>Show all {trades.length}</button>
        )}
      </section>

      {p.skipped.length > 0 && (
        <details className="card text-sm">
          <summary className="cursor-pointer font-medium">Signals not taken ({p.skipped.length}) and why</summary>
          <ul className="mt-2 space-y-1">
            {p.skipped.slice(-40).reverse().map((k, i) => <li key={i}><span className="font-mono text-xs">{k.date}</span> {k.symbol}: <span className="muted">{k.reason}</span></li>)}
          </ul>
        </details>
      )}
    </div>
  );
}
