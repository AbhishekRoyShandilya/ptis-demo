import { useState } from "react";
import { Link } from "react-router-dom";
import { inr, useData } from "../data";
import type { Evaluation, Scan } from "../types";
import { Loading, StatusChip, Title } from "../components/ui";

function SignalChip({ e }: { e: Evaluation }) {
  if (e.valid) return <span className="chip bg-teal-100 text-teal-800 dark:bg-teal-900/50 dark:text-teal-200">signal</span>;
  if (e.disqualified) return <span className="chip bg-rose-100 text-rose-800 dark:bg-rose-900/50 dark:text-rose-200">disqualified</span>;
  return <span className="chip bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300">no</span>;
}

function Row({ e, rank }: { e: Evaluation; rank: number }) {
  const [open, setOpen] = useState(rank <= 3 && e.valid);
  return (
    <>
      <tr
        className="cursor-pointer border-b border-slate-100 hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/40"
        onClick={() => setOpen(!open)}
      >
        <td className="td num muted">{rank}</td>
        <td className="td font-medium">
          <Link onClick={(ev) => ev.stopPropagation()} className="text-teal-700 hover:underline dark:text-teal-300" to={`/market/${encodeURIComponent(e.symbol)}`}>
            {e.symbol}
          </Link>
        </td>
        <td className="td"><SignalChip e={e} /></td>
        <td className="td num">{e.score.toFixed(2)}</td>
        <td className="td num">{e.required_met}/{e.required_total}</td>
        <td className="td num">{e.supporting_met}/{e.supporting_total}</td>
        <td className="td text-xs">{e.regime.replace(/_/g, " ")}</td>
        <td className="td num">{inr(e.close, 2)}</td>
        <td className="td muted">{open ? "▾" : "▸"}</td>
      </tr>
      {open && (
        <tr className="border-b border-slate-100 bg-slate-50/60 dark:border-slate-800/60 dark:bg-slate-900/60">
          <td />
          <td colSpan={8} className="px-3 py-3">
            {e.disqualified && <p className="mb-2 text-sm text-rose-700 dark:text-rose-300">Disqualified: {e.disqualification_reason}</p>}
            <ul className="space-y-1.5">
              {e.conditions.map((c) => (
                <li key={c.type} className="flex flex-wrap items-center gap-2 text-sm">
                  <StatusChip status={c.status} category={c.category} />
                  <span className="font-mono text-xs">{c.type}</span>
                  <span className="text-xs muted">{c.category === "avoid" ? "avoid" : c.required ? "required" : `supporting ×${c.weight}`}</span>
                  <span className="text-xs">{c.details}</span>
                </li>
              ))}
            </ul>
          </td>
        </tr>
      )}
    </>
  );
}

export default function ScannerPage() {
  const { data, error } = useData<Scan>("scan.json");
  const [all, setAll] = useState(false);
  if (!data) return <Loading error={error} />;
  const shown = all ? data.evaluations : data.evaluations.slice(0, 15);
  return (
    <div className="space-y-4">
      <Title
        sub={`Every stock evaluated against the strategy template on the ${data.as_of} close by the PTIS StrategyMatcher, ranked by its score. Click a row for the condition-by-condition checklist the engine produced.`}
      >
        Scanner
      </Title>
      {data.next_session_entries.length > 0 && (
        <div className="card text-sm">
          <b>Paper entries queued for the next open: </b>
          {data.next_session_entries.map((n) => `${n.symbol} (stop ${inr(n.stop, 2)})`).join(", ")}
        </div>
      )}
      <div className="card overflow-x-auto p-0">
        <table className="w-full min-w-[720px]">
          <thead className="border-b border-slate-200 dark:border-slate-800">
            <tr>
              <th className="th num">#</th>
              <th className="th">Symbol</th>
              <th className="th">Signal</th>
              <th className="th num">Score</th>
              <th className="th num">Required</th>
              <th className="th num">Supporting</th>
              <th className="th">Regime</th>
              <th className="th num">Close</th>
              <th className="th" />
            </tr>
          </thead>
          <tbody>
            {shown.map((e, i) => (
              <Row key={e.symbol} e={e} rank={i + 1} />
            ))}
          </tbody>
        </table>
      </div>
      {!all && data.evaluations.length > 15 && (
        <button className="text-sm text-teal-700 underline dark:text-teal-300" onClick={() => setAll(true)}>
          Show all {data.evaluations.length}
        </button>
      )}
    </div>
  );
}
