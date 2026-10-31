// Prompt: Define a TypeScript schema for an AI-native spreadsheet where each cell
// can contain raw data, a traditional formula, or an agentic prompt with its
// associated metadata.
//
// Source of truth for the wire format. Keep in sync with
// packages/agents/app/models.py (Pydantic) and packages/core CellKind (Rust).

/** A1-style reference, e.g. "B12". */
export type CellRef = string;

export type Primitive = string | number | boolean | null;

/** Lifecycle of an agentic cell, rendered by the grid. */
export type AgentStatus = "idle" | "loading" | "thinking" | "verified" | "error";

export interface AgentMetadata {
  model?: string | null;
  tools: string[];
  last_run_at?: string | null; // ISO 8601
  error?: string | null;
}

export interface RawContent {
  type: "raw";
  value: Primitive;
}

export interface FormulaContent {
  type: "formula";
  /** e.g. "=SUM(A1:A3)" */
  expression: string;
  /** Natural-language instruction the formula was generated from, if any. */
  source_prompt?: string | null;
}

export interface AgentPromptContent {
  type: "agentPrompt";
  prompt: string;
  status: AgentStatus;
  metadata: AgentMetadata;
}

export type CellContent = RawContent | FormulaContent | AgentPromptContent;

export interface Cell {
  ref: CellRef;
  content: CellContent;
  /** Last computed / displayed value. */
  value: Primitive;
  updated_at: string;
}

export interface Sheet {
  id: string;
  name: string;
  rows: number;
  cols: number;
  cells: Record<CellRef, Cell>;
  created_at: string;
  updated_at: string;
}

// ---- API payloads -----------------------------------------------------------

export interface SheetCreate {
  name: string;
  rows?: number;
  cols?: number;
}

export interface CellUpdate {
  content: CellContent;
}

export interface AgentRunRequest {
  prompt: string;
  context?: Record<string, unknown>;
  sheet_id?: string;
  cell_ref?: CellRef;
}

export interface ToolCall {
  tool: string;
  input: string;
  output: string;
}

export interface AgentRunResponse {
  result: string;
  status: AgentStatus;
  tool_calls: ToolCall[];
  trace: string[];
  cell: Cell | null;
}

export interface FormulaTranslateResponse {
  formula: string;
  explanation: string;
  confidence: number;
  source: "rules" | "llm";
}

export interface Anomaly {
  column: string;
  row: number | null;
  kind: string;
  message: string;
  suggestion?: string | null;
}

export interface CleaningReport {
  row_count: number;
  anomaly_count: number;
  anomalies: Anomaly[];
}

// ---- helpers ----------------------------------------------------------------

export const isAgentCell = (c: CellContent): c is AgentPromptContent => c.type === "agentPrompt";

export function colToLetters(col: number): string {
  let n = col + 1;
  let s = "";
  while (n > 0) {
    const r = (n - 1) % 26;
    s = String.fromCharCode(65 + r) + s;
    n = Math.floor((n - 1) / 26);
  }
  return s;
}

export const toRef = (row: number, col: number): CellRef => `${colToLetters(col)}${row + 1}`;
