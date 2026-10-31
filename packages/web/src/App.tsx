import { useCallback, useEffect, useState } from "react";
import type { CellContent, CellRef, Sheet } from "@shared/spreadsheet_schema";
import { api } from "./api/client";
import { AgentPanel } from "./components/AgentPanel/AgentPanel";
import { FormulaBar } from "./components/FormulaBar/FormulaBar";
import { CellRenderer } from "./components/Grid/CellRenderer";

export default function App() {
  const [sheet, setSheet] = useState<Sheet | null>(null);
  const [selected, setSelected] = useState<CellRef | null>("A1");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const sheets = await api.listSheets();
        setSheet(sheets[0] ?? (await api.createSheet({ name: "Untitled", rows: 50, cols: 12 })));
      } catch (e) {
        setError(`Agents API unreachable: ${e instanceof Error ? e.message : e}`);
      }
    })();
  }, []);

  const refresh = useCallback(async () => {
    if (sheet) setSheet(await api.getSheet(sheet.id));
  }, [sheet]);

  const commit = async (content: CellContent) => {
    if (!sheet || !selected) return;
    await api.updateCell(sheet.id, selected, content);
    if (content.type === "agentPrompt") {
      markPending(selected);
      await api.runAgent({ prompt: content.prompt, sheet_id: sheet.id, cell_ref: selected });
    }
    await refresh();
  };

  // Optimistically show the "thinking" state until the API responds.
  const markPending = (ref: CellRef) =>
    setSheet((s) => {
      const cell = s?.cells[ref];
      if (!s || !cell || cell.content.type !== "agentPrompt") return s;
      return {
        ...s,
        cells: { ...s.cells, [ref]: { ...cell, content: { ...cell.content, status: "thinking" } } },
      };
    });

  return (
    <div className="app">
      <header className="app-header">
        <h1>OpenSheet</h1>
        <span>{sheet?.name}</span>
        {error && <span className="error">{error}</span>}
      </header>
      <FormulaBar selected={selected} cell={selected ? sheet?.cells[selected] : undefined} onCommit={commit} />
      <div className="app-body">
        <div className="grid-wrap">
          {sheet && (
            <CellRenderer
              rows={sheet.rows}
              cols={sheet.cols}
              cells={sheet.cells}
              selected={selected}
              onSelect={setSelected}
            />
          )}
        </div>
        <AgentPanel sheetId={sheet?.id ?? null} selected={selected} onCellUpdated={refresh} onPending={markPending} />
      </div>
    </div>
  );
}
