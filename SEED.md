Act as a Principal Software Architect. Initialize the directory structure for 'opensheet-ai', a high-performance, AI-native spreadsheet.

Generate the following file hierarchy:
- `/packages/core/src/engine/wasm_grid.rs`
- `/packages/web/src/components/Grid/CellRenderer.tsx`
- `/packages/agents/src/orchestrator/cell_agent.py`
- `/packages/shared/types/spreadsheet_schema.ts`
- `/docker-compose.yml`
- `README.md`

Inside each file, add a single comment as a generation prompt:
- wasm_grid.rs: "# Prompt: Implement a high-performance Rust-based grid engine that manages cell dependencies and triggers agentic updates via WebAssembly."
- CellRenderer.tsx: "# Prompt: Create a React component using HTML5 Canvas to render a spreadsheet grid that supports 'agentic states' (loading, thinking, and verified)."
- cell_agent.py: "# Prompt: Write a Python agent using LangGraph that interprets natural language instructions from a cell, executes necessary tools (like web search), and returns the formatted result."
- spreadsheet_schema.ts: "# Prompt: Define a TypeScript schema for an AI-native spreadsheet where each cell can contain raw data, a traditional formula, or an agentic prompt with its associated metadata."
