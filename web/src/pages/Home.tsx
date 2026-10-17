import { Link } from "react-router-dom";
import { LINKS } from "../config";
import { useData } from "../data";
import type { Meta } from "../types";
import { Stat, Title } from "../components/ui";

const PIPELINE = [
  { step: "1", title: "Fetch", body: "NSE's public end-of-day bhavcopy for the NIFTY 50, every weekday evening.", code: "demo/eod.py" },
  { step: "2", title: "Clean", body: "Back-adjust splits and bonuses (the archive's previous close is not adjusted). Every adjustment is logged.", code: "demo/eod.py" },
  { step: "3", title: "Perceive", body: "Indicators and market regime per stock, computed only from data up to that day.", code: "strategy_engine/indicators.py · regime_detector.py" },
  { step: "4", title: "Match", body: "The taught strategy template is evaluated condition by condition; the matcher scores and ranks every stock.", code: "strategy_engine/strategy_matcher.py" },
  { step: "5", title: "Trade (paper)", body: "Signals on the close, entries at the next open. Sizing with drawdown and portfolio-heat limits; delivery costs.", code: "position_sizer.py · analytics/charges.py" },
  { step: "6", title: "Publish", body: "Results are written as JSON and this static site shows them. No server, no database, no keys.", code: "demo/build.py" },
];

export default function Home() {
  const { data: meta } = useData<Meta>("meta.json");
  return (
    <div className="space-y-8">
      <Title sub={<>
        PTIS (Personal Trading Intelligence System) is a platform I built for researching, journaling and
        paper-trading Indian equities. This page runs its <b>real strategy engine</b> every evening on <b>real NSE
        prices</b>, with a textbook strategy taught to it as a template, so you can see each piece working.
      </>}>
        A trading-intelligence engine, running live on end-of-day data
      </Title>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Data as of" value={meta?.data_as_of ?? "…"} note="last NSE session" />
        <Stat label="Sessions processed" value={meta?.sessions ?? "…"} note={meta ? `since ${meta.first_session}` : ""} />
        <Stat label="Stocks scanned" value={meta?.symbols ?? "…"} note="today's NIFTY 50" />
        <Stat label="Signals today" value={meta?.valid_signals_today ?? "…"} note={<Link className="text-teal-700 underline dark:text-teal-300" to="/scanner">open the scanner</Link>} />
      </div>

      <section>
        <h2 className="mb-3 text-lg font-semibold">What happens every evening</h2>
        <ol className="grid gap-3 md:grid-cols-3">
          {PIPELINE.map((p) => (
            <li key={p.step} className="card">
              <div className="flex items-center gap-2">
                <span className="grid h-6 w-6 place-items-center rounded-full bg-teal-700 text-xs font-semibold text-white">{p.step}</span>
                <span className="font-medium">{p.title}</span>
              </div>
              <p className="mt-2 text-sm">{p.body}</p>
              <p className="mt-2 font-mono text-xs muted">{p.code}</p>
            </li>
          ))}
        </ol>
        <p className="mt-3 text-sm muted">
          Steps 3–5 are the public PTIS code, used unchanged. The demo only prepares inputs and publishes outputs.
          {meta && <> Last run: {new Date(meta.generated_at).toLocaleString()} in {meta.timings.total_s}s.</>}
        </p>
      </section>

      <section className="grid gap-3 md:grid-cols-2">
        <div className="card">
          <h3 className="font-medium">How a strategy is "taught"</h3>
          <p className="mt-2 text-sm">
            In PTIS a strategy is a template: entry conditions (required or supporting, each with a weight), conditions
            to avoid, regimes it prefers, exits and risk rules. The condition engine evaluates each one against market
            data and returns met / not met / inconclusive, with the numbers behind it. That is what produces the
            checklists on the <Link className="text-teal-700 underline dark:text-teal-300" to="/scanner">scanner</Link>.
            See the <Link className="text-teal-700 underline dark:text-teal-300" to="/strategy">strategy</Link> used here.
          </p>
        </div>
        <div className="card">
          <h3 className="font-medium">Honest by construction</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
            <li>No look-ahead: a signal uses data up to that day's close; the trade happens at the next open.</li>
            <li>If a daily bar touches both the stop and the target, the stop is assumed first.</li>
            <li>Results are shown with their weaknesses (sample size, median trade, concentration).</li>
            <li>The universe is today's NIFTY 50 applied to the past: that is survivorship-biased, and said so.</li>
          </ul>
        </div>
      </section>

      <section className="card">
        <h3 className="font-medium">What this demo is not</h3>
        <p className="mt-2 text-sm">
          It is not my trading system, and the strategy is a textbook example, not a recommendation. The full PTIS
          also has a trade journal with strategy attribution, behavioural analytics, shadow trading, an intraday
          virtual trader and an AI coach; those need a live account and intraday feeds, so they are described in the
          repository rather than run here. The demo is fully separate from any real trading setup: different
          repository, data, hosting, and no credentials of any kind.
        </p>
        <div className="mt-3 flex flex-wrap gap-3 text-sm">
          {LINKS.ptisRepo && <a className="text-teal-700 underline dark:text-teal-300" href={LINKS.ptisRepo}>PTIS source</a>}
          {LINKS.engineeringNotes && <a className="text-teal-700 underline dark:text-teal-300" href={LINKS.engineeringNotes}>Engineering notes</a>}
          {LINKS.demoRepo && <a className="text-teal-700 underline dark:text-teal-300" href={LINKS.demoRepo}>This demo's source and nightly run logs</a>}
          <Link className="text-teal-700 underline dark:text-teal-300" to="/system">System status</Link>
        </div>
      </section>
    </div>
  );
}
