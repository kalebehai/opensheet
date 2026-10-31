# OpenSheet

OpenSheet is an open-source, AI-native spreadsheet platform designed to do for data analysis what Cursor did for software engineering. Unlike traditional spreadsheets where formulas are manually entered, OpenSheet integrates autonomous agents directly into the grid. It treats cells not just as static data points, but as dynamic prompts and agentic nodes capable of reasoning, data fetching, and automated cleaning.

## Features
- **Agentic Cells:** Assign specific tasks to cells (e.g., "Find the current stock price of $TICKER and calculate the P/E ratio").
- **Natural Language Formulas:** Replace complex VLOOKUPs and nested IF statements with plain English instructions.
- **Autonomous Data Cleaning:** Background agents that identify anomalies, format dates, and suggest structural improvements.
- **Collaborative AI:** Multi-agent workflows where one agent fetches data while another summarizes it in an adjacent column.

## Architecture

OpenSheet is a monorepo with four packages:

```
packages/
├── core/     Rust grid engine (compiled to WebAssembly)
├── agents/   Python FastAPI service: cell agents, NL formulas, data cleaning
├── shared/   TypeScript schema shared by the web app (mirrored in Pydantic and Rust)
└── web/      Vite + React + TypeScript front end with a canvas grid
```

```
┌──────────────────────────── browser ─────────────────────────────┐
│  web (React)                                                      │
│   FormulaBar ─┐                                                   │
│   CellRenderer (canvas, agent states) ◄── core (WASM): dependency │
│   AgentPanel ─┘                           graph, recalc order     │
└───────────────────────┬──────────────────────────────────────────┘
                        │ REST (JSON)
┌───────────────────────▼──────────────────────────────────────────┐
│  agents (FastAPI)                                                 │
│   routers ─► orchestrator: CellAgent (plan → act → respond →      │
│              verify), ToolRegistry, LLMClient, formula translator,│
│              cleaning scanner                                     │
│   repository (in-memory for now)                                  │
└───────────────────────────────────────────────────────────────────┘
```

- **Cells** are one of three kinds: `raw`, `formula` or `agentPrompt`. Agent cells carry a status
  (`idle → loading → thinking → verified`, or `error`) that the grid renders as badges.
  See `packages/shared/types/spreadsheet_schema.ts`.
- **core** keeps a sparse grid plus a dependency graph. When a cell changes, it returns the
  topological recalculation order, rejects circular references, and reports which downstream
  agent cells need to run again.
- **agents** runs a graph-style agent per cell. LLM access goes through an `LLMClient` interface.
  The default `StubLLM` is deterministic and needs no API keys.

## Getting started

Prerequisites: Python 3.11+, Node 20+, and Rust (stable) for the engine. Docker is optional.

```bash
cp .env.example .env

# Agents API → http://localhost:8000 (OpenAPI docs at /docs)
cd packages/agents && pip install -e ".[dev]" && uvicorn app.main:app --reload

# Web app → http://localhost:5173
cd packages/web && npm install && npm run dev

# Rust engine
cd packages/core && cargo test
```

Or run everything with Docker: `docker compose up --build`.

`make help` lists shortcuts (`make test` runs the Rust tests, pytest and the TypeScript check).

In the formula bar, type a plain value, a formula starting with `=`, or a prompt starting with `?`
to create an agent cell.

## API

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/health` | Liveness check and active LLM provider |
| `GET` | `/sheets` | List sheets |
| `POST` | `/sheets` | Create a sheet (`name`, `rows`, `cols`) |
| `GET` | `/sheets/{id}` | Get a sheet with its cells |
| `PATCH` | `/sheets/{id}` | Rename or resize a sheet |
| `DELETE` | `/sheets/{id}` | Delete a sheet |
| `PATCH` | `/sheets/{id}/cells/{ref}` | Set a cell (`raw`, `formula` or `agentPrompt` content) |
| `POST` | `/agents/run` | Run a cell agent on a prompt, optionally writing the result to `sheet_id` + `cell_ref` |
| `POST` | `/formulas/translate` | Turn a natural-language instruction into a formula |
| `POST` | `/cleaning/scan` | Report anomalies: missing values, whitespace, type mismatches, outliers, mixed date formats, duplicate rows |

## Roadmap

- [x] Monorepo scaffold: engine, API, shared schema, canvas grid
- [ ] Formula parser and evaluator in `core`, plus a wasm-pack build used by the web app
- [ ] Real LLM providers behind `LLMClient`, and tool selection through function calling
- [ ] Web search and data-fetch tools with API keys from `.env`
- [ ] Stream agent state (loading → thinking → verified) over SSE or WebSocket
- [ ] Persistent storage (SQLite/Postgres) in place of the in-memory repository
- [ ] Multi-agent column workflows (one agent fetches, another summarizes the next column)
- [ ] Background cleaning agents that suggest and apply fixes
- [ ] Grid virtualization, editing UX, and real-time collaboration

## License

[MIT](LICENSE) © 2026 Kaleb B. Haile
