export interface Meta {
  generated_at: string; data_as_of: string; sessions: number; symbols: number; rows: number; first_session: string;
  download: Record<string, number | string>; adjustments: number; timings: Record<string, number>;
  engine_source: string[]; python: string; evaluations_today: number; valid_signals_today: number;
}
export interface Condition {
  type: string; category: "confirmation" | "avoid" | "invalidation"; status: string; required: boolean;
  weight: number; details: string; actual: string | null; expected: string | null;
}
export interface Evaluation {
  symbol: string; date: string; close: number; regime: string; regime_confidence: number; regime_note: string;
  score: number; valid: boolean; required_met: number; required_total: number; supporting_met: number;
  supporting_total: number; avoid_triggered: number; disqualified: boolean; disqualification_reason: string;
  conditions: Condition[];
}
export interface Scan { as_of: string; evaluations: Evaluation[]; next_session_entries: { symbol: string; score: number; stop: number; close: number }[]; }
export interface StockRow {
  symbol: string; date: string; close: number; change_pct: number; ema_20: number; ema_50: number; ema_200: number | null;
  rsi_14: number; regime: string | null; score: number | null; valid: boolean; spark: number[];
}
export interface Market { as_of: string; stocks: StockRow[]; }
export interface Bar { d: string; o: number; h: number; l: number; c: number; v: number; e20: number; e50: number; }
export interface Fill { date: string; qty: number; price: number; reason: string; cost: number; }
export interface ClosedTrade { symbol: string; entry_date: string; entry: number; qty: number; stop: number; exit_date: string; pnl: number; r: number; sessions: number; signal_score: number; fills: Fill[]; }
export interface OpenPos { symbol: string; entry_date: string; entry: number; qty: number; qty_left: number; stop: number; t1: number; t2: number; last: number; unrealised: number; sessions: number; fills: Fill[]; }
export interface Paper {
  stats: Record<string, number | string | null>;
  rules: { capital: number; max_positions: number; paper_start: string };
  equity_curve: { date: string; equity: number; drawdown_pct: number; positions: number }[];
  closed: ClosedTrade[]; open: OpenPos[]; skipped: { date: string; symbol: string; reason: string }[];
  signals: { date: string; symbol: string; close: number; score: number; stop: number }[];
  next_session: { symbol: string; score: number; stop: number; close: number }[];
}
export interface StrategyDoc {
  id: string; name: string; description: string; yaml: string; direction: string;
  regimes: { preferred: string[]; avoid: string[] };
  confirmations: { type: string; required: boolean; weight: number; description: string; params: Record<string, unknown> }[];
  avoid_conditions: { type: string; description: string; params: Record<string, unknown> }[];
  exit: { stop: { type: string; params: Record<string, unknown> }; targets: { r: number; size_pct: number }[]; max_sessions: number };
  risk: { max_risk_pct: number };
}
export interface Adjustment { symbol: string; date: string; ratio: number; open: number; prev_close: number; isin_changed: boolean; }
