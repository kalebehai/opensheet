"""Pydantic models. Keep in sync with packages/shared/types/spreadsheet_schema.ts."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Annotated, Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(UTC)


class AgentStatus(str, Enum):
    idle = "idle"
    loading = "loading"
    thinking = "thinking"
    verified = "verified"
    error = "error"


class AgentMetadata(BaseModel):
    model: str | None = None
    tools: list[str] = Field(default_factory=list)
    last_run_at: datetime | None = None
    error: str | None = None


class RawContent(BaseModel):
    type: Literal["raw"] = "raw"
    value: str | float | bool | None = None


class FormulaContent(BaseModel):
    type: Literal["formula"] = "formula"
    expression: str
    source_prompt: str | None = None  # set when generated from natural language


class AgentPromptContent(BaseModel):
    type: Literal["agentPrompt"] = "agentPrompt"
    prompt: str
    status: AgentStatus = AgentStatus.idle
    metadata: AgentMetadata = Field(default_factory=AgentMetadata)


CellContent = Annotated[
    RawContent | FormulaContent | AgentPromptContent, Field(discriminator="type")
]


class Cell(BaseModel):
    ref: str
    content: CellContent
    value: Any = None  # last computed / displayed value
    updated_at: datetime = Field(default_factory=_now)


class Sheet(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str
    rows: int = 100
    cols: int = 26
    cells: dict[str, Cell] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class SheetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    rows: int = Field(default=100, ge=1, le=1_000_000)
    cols: int = Field(default=26, ge=1, le=16_384)


class SheetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    rows: int | None = Field(default=None, ge=1, le=1_000_000)
    cols: int | None = Field(default=None, ge=1, le=16_384)


class CellUpdate(BaseModel):
    content: CellContent


class AgentRunRequest(BaseModel):
    prompt: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    sheet_id: str | None = None
    cell_ref: str | None = None  # when set with sheet_id, the result is written back


class ToolCall(BaseModel):
    tool: str
    input: str
    output: str


class AgentRunResponse(BaseModel):
    result: str
    status: AgentStatus
    tool_calls: list[ToolCall]
    trace: list[str]
    cell: Cell | None = None


class FormulaTranslateRequest(BaseModel):
    text: str = Field(min_length=1)


class FormulaTranslateResponse(BaseModel):
    formula: str
    explanation: str
    confidence: float
    source: str


class CleaningScanRequest(BaseModel):
    headers: list[str]
    rows: list[list[Any]]


class AnomalyOut(BaseModel):
    column: str
    row: int | None
    kind: str
    message: str
    suggestion: str | None = None


class CleaningReport(BaseModel):
    row_count: int
    anomaly_count: int
    anomalies: list[AnomalyOut]
