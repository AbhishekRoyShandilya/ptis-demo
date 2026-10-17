# PTIS public demo

A live, static website that runs the **public PTIS strategy engine** every weekday evening on **real NSE end-of-day
prices**, with a textbook strategy taught to it as a template. Anyone opening the link can see each part working:
the market data, the strategy template, the engine's ranked scan with a condition-by-condition checklist, and a
paper trader with its full trade log.

> The strategy is an illustrative textbook example, not a recommendation and not the author's trading system.

## How it works

```
GitHub Actions, 19:30 IST on weekdays
  1  fetch     NSE bhavcopy (public end-of-day archive) for today's NIFTY 50          demo/eod.py
  2  clean     back-adjust splits/bonuses; list suspicious opening prints              demo/eod.py, demo/build.py
  3  perceive  indicators + market regime per stock (data up to that day only)         PTIS strategy_engine
  4  match     evaluate the strategy template, score and rank every stock             PTIS StrategyMatcher
  5  trade     paper trader: signal on the close, entry at the next open,              demo/paper.py on PTIS
               PositionSizer limits, delivery costs                                    PositionSizer + CostModel
  6  test      isolation, corporate actions, truncation (no look-ahead) + leak control tests/
  7  publish   JSON -> static React site on GitHub Pages                               web/
```

Steps 3–5 use the public PTIS code, vendored unchanged in `vendor/ptis` (its source export and hash are recorded in
`vendor/VENDORED_FROM.txt`). The demo only prepares inputs and publishes outputs.

## Isolation

The demo is deliberately separated from any real trading setup:

- its own repository, data (`data/`), hosting and environment
- no broker, alert, cloud or AI credentials; `demo/guard.py` refuses to run if any such key, any `.env` file, a
  database server URL, or the private PTIS repository on the import path is present
- no database server: the engine runs in memory and the site is static JSON
- code flows one way only: public PTIS export → `scripts/sync_vendor.py` → `vendor/ptis` (the sync refuses the private
  repository)

## Honest by construction

- **No look-ahead.** Signals use data up to that session's close; entries are at the next open.
  `tests/test_demo.py` re-runs the paper trader on data cut off mid-year and requires every signal, trade and equity
  value up to the cut to be identical. A positive control plants a 10-day look-ahead and requires the same comparison
  to fail.
- **Conservative fills.** If a daily bar touches both the stop and a target, the stop is assumed to come first. A stop
  gapped through at the open exits at the open.
- **Data corrections are public.** The archive's previous close is not split-adjusted, so standard split/bonus gaps are
  detected (within 3% of a standard ratio) and back-adjusted. Each one is listed on the System page, together with
  isolated opening prints that may affect results.
- **Known limitations, stated on the site.** The universe is today's NIFTY 50 applied to the past
  (survivorship-biased); dividends are not added back; the cost model is PTIS's intraday model with delivery
  parameters.

## Run it locally

```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt     # Windows; use .venv/bin on Linux/macOS
python -m demo.build              # downloads missing sessions, runs the engine, writes web/public/data/
python -m pytest tests -q
cd web && npm ci && npm run dev
```

## Deploying

1. Create a GitHub repository and push this folder.
2. Settings → Pages → Source: **GitHub Actions**.
3. Run the `nightly` workflow once by hand (Actions → nightly → Run workflow). After that it runs every weekday
   evening; a stale or failed download turns the run red instead of quietly showing old numbers.

## How it was built

Built with AI pair-programming (Claude Code), as was PTIS itself.
