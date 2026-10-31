// Prompt: Create a React component using HTML5 Canvas to render a spreadsheet
// grid that supports 'agentic states' (loading, thinking, and verified).

import { useEffect, useRef, type MouseEvent } from "react";
import {
  colToLetters,
  toRef,
  type AgentStatus,
  type Cell,
  type CellRef,
} from "@shared/spreadsheet_schema";

export interface CellRendererProps {
  rows: number;
  cols: number;
  cells: Record<CellRef, Cell>;
  selected: CellRef | null;
  onSelect: (ref: CellRef) => void;
  cellWidth?: number;
  cellHeight?: number;
}

const HEADER_W = 48;
const HEADER_H = 24;

const STATUS_COLOR: Record<AgentStatus, string> = {
  idle: "#8c959f",
  loading: "#bf8700",
  thinking: "#8250df",
  verified: "#1a7f37",
  error: "#cf222e",
};

function displayValue(cell: Cell | undefined): string {
  if (!cell) return "";
  if (cell.value !== null && cell.value !== undefined && cell.value !== "") return String(cell.value);
  switch (cell.content.type) {
    case "raw":
      return cell.content.value === null ? "" : String(cell.content.value);
    case "formula":
      return cell.content.expression;
    case "agentPrompt":
      return cell.content.status === "idle" ? `✦ ${cell.content.prompt}` : "";
  }
}

/** Draws the badge for an agentic cell. `t` animates loading/thinking states. */
function drawAgentBadge(ctx: CanvasRenderingContext2D, status: AgentStatus, x: number, y: number, w: number, h: number, t: number) {
  const color = STATUS_COLOR[status];
  ctx.fillStyle = color;
  ctx.fillRect(x, y, 3, h); // left accent bar

  const cx = x + w - 10;
  const cy = y + h / 2;
  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.lineWidth = 2;
  if (status === "loading") {
    const a = (t / 150) % (Math.PI * 2);
    ctx.beginPath();
    ctx.arc(cx, cy, 5, a, a + Math.PI * 1.5);
    ctx.stroke();
  } else if (status === "thinking") {
    for (let i = 0; i < 3; i++) {
      const alpha = 0.3 + 0.7 * Math.abs(Math.sin(t / 300 + i));
      ctx.globalAlpha = alpha;
      ctx.beginPath();
      ctx.arc(cx - 10 + i * 5, cy, 1.8, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  } else if (status === "verified") {
    ctx.beginPath();
    ctx.moveTo(cx - 4, cy);
    ctx.lineTo(cx - 1, cy + 3);
    ctx.lineTo(cx + 4, cy - 3);
    ctx.stroke();
  } else if (status === "error") {
    ctx.font = "bold 12px system-ui";
    ctx.fillText("!", cx - 2, cy + 4);
  }
}

export function CellRenderer({
  rows,
  cols,
  cells,
  selected,
  onSelect,
  cellWidth = 100,
  cellHeight = 24,
}: CellRendererProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const width = HEADER_W + cols * cellWidth;
  const height = HEADER_H + rows * cellHeight;

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;

    const animating = Object.values(cells).some(
      (c) => c.content.type === "agentPrompt" && (c.content.status === "loading" || c.content.status === "thinking"),
    );
    let frame = 0;

    const draw = (t: number) => {
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, width, height);
      ctx.font = "13px system-ui";
      ctx.textBaseline = "middle";

      // Headers
      ctx.fillStyle = "#f6f8fa";
      ctx.fillRect(0, 0, width, HEADER_H);
      ctx.fillRect(0, 0, HEADER_W, height);
      ctx.fillStyle = "#656d76";
      for (let c = 0; c < cols; c++) {
        ctx.fillText(colToLetters(c), HEADER_W + c * cellWidth + cellWidth / 2 - 4, HEADER_H / 2);
      }
      for (let r = 0; r < rows; r++) {
        ctx.fillText(String(r + 1), 8, HEADER_H + r * cellHeight + cellHeight / 2);
      }

      // Gridlines
      ctx.strokeStyle = "#d0d7de";
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let c = 0; c <= cols; c++) {
        const x = HEADER_W + c * cellWidth + 0.5;
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
      }
      for (let r = 0; r <= rows; r++) {
        const y = HEADER_H + r * cellHeight + 0.5;
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
      }
      ctx.stroke();

      // Cells (sparse: only draw populated ones)
      for (const cell of Object.values(cells)) {
        const m = /^([A-Z]+)(\d+)$/.exec(cell.ref);
        if (!m) continue;
        const col = [...m[1]].reduce((n, ch) => n * 26 + ch.charCodeAt(0) - 64, 0) - 1;
        const row = Number(m[2]) - 1;
        if (row >= rows || col >= cols) continue;
        const x = HEADER_W + col * cellWidth;
        const y = HEADER_H + row * cellHeight;

        ctx.save();
        ctx.beginPath();
        ctx.rect(x + 1, y + 1, cellWidth - 2, cellHeight - 2);
        ctx.clip();
        if (cell.content.type === "agentPrompt") {
          ctx.fillStyle = "#fbfaff";
          ctx.fillRect(x + 1, y + 1, cellWidth - 2, cellHeight - 2);
          drawAgentBadge(ctx, cell.content.status, x + 1, y + 1, cellWidth - 2, cellHeight - 2, t);
        }
        ctx.fillStyle = cell.content.type === "formula" ? "#0550ae" : "#1f2328";
        ctx.fillText(displayValue(cell), x + 8, y + cellHeight / 2, cellWidth - 28);
        ctx.restore();
      }

      // Selection
      if (selected) {
        const m = /^([A-Z]+)(\d+)$/.exec(selected);
        if (m) {
          const col = [...m[1]].reduce((n, ch) => n * 26 + ch.charCodeAt(0) - 64, 0) - 1;
          const row = Number(m[2]) - 1;
          ctx.strokeStyle = "#0969da";
          ctx.lineWidth = 2;
          ctx.strokeRect(HEADER_W + col * cellWidth + 1, HEADER_H + row * cellHeight + 1, cellWidth - 2, cellHeight - 2);
        }
      }

      if (animating) frame = requestAnimationFrame(draw);
    };

    frame = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(frame);
  }, [rows, cols, cells, selected, width, height, cellWidth, cellHeight]);

  const handleClick = (e: MouseEvent<HTMLCanvasElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const col = Math.floor((e.clientX - rect.left - HEADER_W) / cellWidth);
    const row = Math.floor((e.clientY - rect.top - HEADER_H) / cellHeight);
    if (row >= 0 && col >= 0 && row < rows && col < cols) onSelect(toRef(row, col));
  };

  // TODO: virtualize (only draw the visible viewport) for large sheets.
  return <canvas ref={canvasRef} onClick={handleClick} role="grid" aria-label="Spreadsheet grid" />;
}

export default CellRenderer;
