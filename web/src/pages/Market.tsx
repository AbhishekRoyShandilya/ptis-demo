import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { inr, pct, useData } from "../data";
import type { Market } from "../types";
import { Loading, Sparkline, Title } from "../components/ui";

type Key = "symbol" | "change_pct" | "score";

export default function MarketPage() {
  const { data, error } = useData<Market>("market.json");
  const [sort, setSort] = useState<Key>("symbol");
  const rows = useMemo(() => {
    if (!data) return [];
    const r = [...data.stocks];
    if (sort === "symbol") r.sort((a, b) => a.symbol.localeCompare(b.symbol));
    else r.sort((a, b) => (b[sort] ?? -1e9) - (a[sort] ?? -1e9));
    return r;
  }, [data, sort]);
  if (!data) return <Loading error={error} />;
  const head = (k: Key, label: string, cls = "") => (
    <th className={`th cursor-pointer select-none ${cls}`} onClick={() => setSort(k)}>{label}{sort === k ? " ↓" : ""}</th>
  );
  return (
    <div>
      <Title sub={`End-of-day prices for today's NIFTY 50, split/bonus adjusted. Regime and score come from the PTIS engine (as of ${data.as_of}).`}>Market</Title>
      <div className="card overflow-x-auto p-0">
        <table className="w-full min-w-[760px]">
          <thead className="border-b border-slate-200 dark:border-slate-800"><tr>
            {head("symbol", "Symbol")}<th className="th">60 sessions</th>
            <th className="th num">Close</th>{head("change_pct", "Day", "num")}
            <th className="th num">EMA 20</th><th className="th num">EMA 50</th><th className="th num">RSI 14</th>
            <th className="th">Regime</th>{head("score", "Strategy score", "num")}
          </tr></thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.symbol} className="border-b border-slate-100 last:border-0 hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/40">
                <td className="td font-medium"><Link className="text-teal-700 hover:underline dark:text-teal-300" to={`/market/${encodeURIComponent(s.symbol)}`}>{s.symbol}</Link></td>
                <td className="td"><Sparkline values={s.spark} up={s.spark[s.spark.length - 1] >= s.spark[0]} /></td>
                <td className="td num">{inr(s.close, 2)}</td>
                <td className={`td num ${s.change_pct >= 0 ? "text-emerald-700 dark:text-emerald-400" : "text-rose-700 dark:text-rose-400"}`}>{pct(s.change_pct)}</td>
                <td className="td num">{inr(s.ema_20, 2)}</td>
                <td className="td num">{inr(s.ema_50, 2)}</td>
                <td className="td num">{s.rsi_14?.toFixed(1)}</td>
                <td className="td text-xs">{s.regime?.replace(/_/g, " ")}</td>
                <td className="td num">{s.score?.toFixed(2)} {s.valid && <span className="chip ml-1 bg-teal-100 text-teal-800 dark:bg-teal-900/50 dark:text-teal-200">signal</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
