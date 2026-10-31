"""OpenSheet agents API entrypoint: `uvicorn app.main:app --reload`."""

import os
import sys
from pathlib import Path

# Make `src/` importable when running from a checkout without `pip install -e`.
_SRC = Path(__file__).resolve().parent.parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from .routers import agents, cleaning, formulas, health, sheets  # noqa: E402

app = FastAPI(title="OpenSheet Agents API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("OPENSHEET_CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (health, sheets, agents, formulas, cleaning):
    app.include_router(r.router)
