import { useEffect, useState, type FormEvent } from "react";
import type { Cell, CellContent, CellRef } from "@shared/spreadsheet_schema";

export interface FormulaBarProps {
  selected: CellRef | null;
  cell: Cell | undefined;
  onCommit: (content: CellContent) => void;
}

/** Text that represents a cell in the bar: "=..." formulas, "?..." agent prompts, else raw. */
function toInput(cell: Cell | undefined): string {
  if (!cell) return "";
  switch (cell.content.type) {
    case "raw":
      return cell.content.value === null ? "" : String(cell.content.value);
    case "formula":
      return cell.content.expression;
    case "agentPrompt":
      return `?${cell.content.prompt}`;
  }
}

export function parseInput(text: string): CellContent {
  if (text.startsWith("=")) return { type: "formula", expression: text };
  if (text.startsWith("?"))
    return { type: "agentPrompt", prompt: text.slice(1).trim(), status: "idle", metadata: { tools: [] } };
  const n = Number(text);
  return { type: "raw", value: text.trim() !== "" && !Number.isNaN(n) ? n : text };
}

export function FormulaBar({ selected, cell, onCommit }: FormulaBarProps) {
  const [text, setText] = useState("");
  useEffect(() => setText(toInput(cell)), [cell, selected]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (selected) onCommit(parseInput(text));
  };

  return (
    <form className="formula-bar" onSubmit={submit}>
      <span className="ref">{selected ?? "-"}</span>
      <input
        value={text}
        disabled={!selected}
        onChange={(e) => setText(e.target.value)}
        placeholder="Value, =FORMULA, or ?ask an agent"
        aria-label="Formula bar"
      />
    </form>
  );
}

export default FormulaBar;
