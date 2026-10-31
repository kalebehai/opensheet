import type {
  AgentRunRequest,
  AgentRunResponse,
  Cell,
  CellContent,
  CellRef,
  CleaningReport,
  FormulaTranslateResponse,
  Sheet,
  SheetCreate,
} from "@shared/spreadsheet_schema";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init.headers },
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new ApiError(res.status, detail?.detail ? JSON.stringify(detail.detail) : res.statusText);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

const json = (body: unknown) => JSON.stringify(body);

export const api = {
  health: () => request<{ status: string; llm: string }>("/health"),

  listSheets: () => request<Sheet[]>("/sheets"),
  getSheet: (id: string) => request<Sheet>(`/sheets/${id}`),
  createSheet: (body: SheetCreate) => request<Sheet>("/sheets", { method: "POST", body: json(body) }),
  updateSheet: (id: string, body: Partial<SheetCreate>) =>
    request<Sheet>(`/sheets/${id}`, { method: "PATCH", body: json(body) }),
  deleteSheet: (id: string) => request<void>(`/sheets/${id}`, { method: "DELETE" }),

  updateCell: (sheetId: string, ref: CellRef, content: CellContent) =>
    request<Cell>(`/sheets/${sheetId}/cells/${ref}`, { method: "PATCH", body: json({ content }) }),

  runAgent: (body: AgentRunRequest) =>
    request<AgentRunResponse>("/agents/run", { method: "POST", body: json(body) }),

  translateFormula: (text: string) =>
    request<FormulaTranslateResponse>("/formulas/translate", { method: "POST", body: json({ text }) }),

  scanCleaning: (headers: string[], rows: unknown[][]) =>
    request<CleaningReport>("/cleaning/scan", { method: "POST", body: json({ headers, rows }) }),
};
