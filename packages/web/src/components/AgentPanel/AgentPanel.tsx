import { useState } from "react";
import type { AgentRunResponse, CellRef, FormulaTranslateResponse } from "@shared/spreadsheet_schema";
import { api } from "../../api/client";

export interface AgentPanelProps {
  sheetId: string | null;
  selected: CellRef | null;
  /** Called after the agent writes into the sheet so the grid can refresh. */
  onCellUpdated: () => void;
  /** Lets the grid show "thinking" while the request is in flight. */
  onPending: (ref: CellRef) => void;
}

export function AgentPanel({ sheetId, selected, onCellUpdated, onPending }: AgentPanelProps) {
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState(false);
  const [run, setRun] = useState<AgentRunResponse | null>(null);
  const [formula, setFormula] = useState<FormulaTranslateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const guard = async (fn: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const runAgent = () =>
    guard(async () => {
      if (selected) onPending(selected);
      const res = await api.runAgent({
        prompt,
        sheet_id: sheetId ?? undefined,
        cell_ref: selected ?? undefined,
      });
      setRun(res);
      onCellUpdated();
    });

  const translate = () => guard(async () => setFormula(await api.translateFormula(prompt)));

  return (
    <aside className="agent-panel">
      <h2>Agent</h2>
      <p>Target cell: <strong>{selected ?? "none"}</strong></p>
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder='e.g. "Calculate 12 * (3 + 4)" or "sum of A1:A10"'
      />
      <div>
        <button disabled={busy || !prompt} onClick={runAgent}>Run agent</button>{" "}
        <button disabled={busy || !prompt} onClick={translate}>To formula</button>
      </div>
      {error && <p className="error">{error}</p>}
      {formula && (
        <section>
          <h3>Formula</h3>
          <pre>{formula.formula || "(none)"}</pre>
          <small>{formula.explanation} · confidence {formula.confidence}</small>
        </section>
      )}
      {run && (
        <section>
          <h3>Result ({run.status})</h3>
          <pre>{run.result}</pre>
          <small>trace: {run.trace.join(" → ")}</small>
          {run.tool_calls.length > 0 && (
            <ul>
              {run.tool_calls.map((c, i) => (
                <li key={i}><code>{c.tool}</code>({c.input}) → {c.output}</li>
              ))}
            </ul>
          )}
        </section>
      )}
      {/* TODO: data-cleaning tab using api.scanCleaning on the selected column. */}
    </aside>
  );
}

export default AgentPanel;
