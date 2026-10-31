# opensheet-agents

FastAPI service behind OpenSheet's agentic cells. See the root README for the endpoint table.

```bash
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
pytest
```

- `app/` — HTTP layer: routers, Pydantic models, in-memory repository.
- `src/orchestrator/` — agent logic: `cell_agent.py` (graph-style agent), tool registry,
  LLM interface (`StubLLM` by default; no API keys needed), formula translator, cleaning scanner.
