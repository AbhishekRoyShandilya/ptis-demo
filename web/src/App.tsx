import { NavLink, Route, Routes } from "react-router-dom";
import { useData } from "./data";
import type { Meta } from "./types";
import Home from "./pages/Home";
import MarketPage from "./pages/Market";
import StockPage from "./pages/Stock";
import StrategyPage from "./pages/Strategy";
import ScannerPage from "./pages/Scanner";
import PaperPage from "./pages/Paper";
import SystemPage from "./pages/System";

const NAV = [
  { to: "/", label: "How it works" },
  { to: "/market", label: "Market" },
  { to: "/strategy", label: "Strategy" },
  { to: "/scanner", label: "Scanner" },
  { to: "/paper", label: "Paper trader" },
  { to: "/system", label: "System" },
];

export default function App() {
  const { data: meta } = useData<Meta>("meta.json");
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/90 backdrop-blur dark:border-slate-800 dark:bg-slate-950/90">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <div className="flex items-center gap-2 font-semibold">
            <span className="grid h-7 w-7 place-items-center rounded-md bg-teal-700 text-sm text-white">P</span>
            PTIS <span className="muted font-normal">public demo</span>
          </div>
          <nav className="flex flex-wrap gap-1 text-sm">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} end={n.to === "/"}
                className={({ isActive }) => `rounded-md px-2.5 py-1.5 ${isActive ? "bg-teal-50 font-medium text-teal-800 dark:bg-teal-900/40 dark:text-teal-200" : "muted hover:text-slate-900 dark:hover:text-white"}`}>
                {n.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto text-xs muted">
            {meta ? <>Data as of <b className="text-slate-700 dark:text-slate-200">{meta.data_as_of}</b> (NSE close)</> : "loading…"}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/market" element={<MarketPage />} />
          <Route path="/market/:symbol" element={<StockPage />} />
          <Route path="/strategy" element={<StrategyPage />} />
          <Route path="/scanner" element={<ScannerPage />} />
          <Route path="/paper" element={<PaperPage />} />
          <Route path="/system" element={<SystemPage />} />
        </Routes>
      </main>
      <footer className="mx-auto max-w-6xl px-4 pb-10 text-xs muted">
        A personal engineering project. Illustrative textbook strategy on end-of-day data; not investment advice and
        not the author's trading system. Prices: NSE end-of-day bhavcopy.
      </footer>
    </div>
  );
}
