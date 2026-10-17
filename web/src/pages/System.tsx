import { useData } from "../data";
import type { Adjustment, Meta } from "../types";
import { Loading, Stat, Title } from "../components/ui";

interface Quality {
  open_prints: { symbol: string; date: string; prev_close: number; open: number; low: number; high: number; close: number }[];
  zero_volume: { symbol: string; date: string }[];
}

export default function SystemPage() {
  const { data: meta, error } = useData<Meta>("meta.json");
  const { data: adj } = useData<Adjustment[]>("adjustments.json");
  const { data: dq } = useData<Quality>("data_quality.json");
  if (!meta) return <Loading error={error} />;
  return (
    <div className="space-y-5">
      <Title sub="How fresh the data is, what the last run did, and every correction made to the raw prices.">System</Title>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Last run" value={new Date(meta.generated_at).toLocaleDateString()} note={new Date(meta.generated_at).toLocaleTimeString()} />
        <Stat label="Run time" value={`${meta.timings.total_s}s`} note={`data ${meta.timings.data_s}s · engine ${meta.timings.engine_s}s`} />
        <Stat label="Rows in panel" value={meta.rows.toLocaleString()} note={`${meta.symbols} stocks × ${meta.sessions} sessions`} />
        <Stat label="Corrections" value={meta.adjustments} note="split / bonus adjustments" />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="card text-sm">
          <h2 className="font-medium">Engine</h2>
          <p className="mt-2">The public PTIS code, vendored unchanged:</p>
          <pre className="mt-2 overflow-x-auto rounded-lg bg-slate-100 p-2 text-xs dark:bg-slate-950">{meta.engine_source.join("\n")}</pre>
          <p className="mt-2 text-xs muted">Python {meta.python}. Downloads this run: {Object.entries(meta.download).map(([k, v]) => `${k} ${v}`).join(", ")}.</p>
        </div>
        <div className="card text-sm">
          <h2 className="font-medium">Isolation</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            <li>Separate repository, data and hosting from any real trading setup.</li>
            <li>No broker, alert, cloud or AI keys: the build refuses to start if any are present.</li>
            <li>No database server: the engine runs in memory and publishes static JSON.</li>
            <li>Source of prices: NSE's public end-of-day bhavcopy archive, plus NSE's NIFTY 50 constituent list.</li>
          </ul>
        </div>
      </div>

      <section className="card text-sm">
        <h2 className="font-medium">Corporate-action adjustments</h2>
        <p className="mt-1 muted">The archive's "previous close" is not adjusted for splits or bonuses. A gap is treated as a corporate action only when it lands within 3% of a standard ratio; earlier prices are then scaled.</p>
        <table className="mt-3 w-full">
          <thead><tr><th className="th">Symbol</th><th className="th">Ex-date</th><th className="th num">Ratio</th><th className="th num">Prev close</th><th className="th num">Open</th><th className="th">ISIN changed</th></tr></thead>
          <tbody>
            {(adj ?? []).map((a) => (
              <tr key={`${a.symbol}${a.date}`} className="border-t border-slate-100 dark:border-slate-800/60">
                <td className="td font-medium">{a.symbol}</td><td className="td">{a.date}</td><td className="td num">{a.ratio}</td>
                <td className="td num">{a.prev_close}</td><td className="td num">{a.open}</td><td className="td">{a.isin_changed ? "yes" : "no"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="card text-sm">
        <h2 className="font-medium">Bars worth a second look</h2>
        <p className="mt-1 muted">Opening prints more than 4% away from both the previous close and the same day's close. They are kept as published (a stop gapped at the open exits at the open), and listed so any result that depends on them is explainable.</p>
        {dq && dq.open_prints.length === 0 && <p className="mt-2">None.</p>}
        {dq && dq.open_prints.length > 0 && (
          <table className="mt-3 w-full">
            <thead><tr><th className="th">Symbol</th><th className="th">Date</th><th className="th num">Prev close</th><th className="th num">Open</th><th className="th num">Low</th><th className="th num">High</th><th className="th num">Close</th></tr></thead>
            <tbody>
              {dq.open_prints.map((r) => (
                <tr key={`${r.symbol}${r.date}`} className="border-t border-slate-100 dark:border-slate-800/60">
                  <td className="td font-medium">{r.symbol}</td><td className="td">{r.date}</td><td className="td num">{r.prev_close}</td>
                  <td className="td num">{r.open}</td><td className="td num">{r.low}</td><td className="td num">{r.high}</td><td className="td num">{r.close}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
