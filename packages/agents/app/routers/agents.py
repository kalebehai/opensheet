from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status

from orchestrator import CellAgent

from ..deps import cell_agent
from ..models import AgentMetadata, AgentPromptContent, AgentRunRequest, AgentRunResponse
from ..repository import SheetRepository, get_repository, normalize_ref

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/run", response_model=AgentRunResponse)
def run_agent(
    body: AgentRunRequest,
    agent: CellAgent = Depends(cell_agent),
    repo: SheetRepository = Depends(get_repository),
):
    # TODO: run asynchronously and stream loading -> thinking -> verified over SSE/WebSocket.
    out = agent.run(body.prompt, body.context)
    cell = None
    if body.sheet_id and body.cell_ref:
        ref = normalize_ref(body.cell_ref)
        if repo.get(body.sheet_id) is None or ref is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "sheet or cell not found")
        content = AgentPromptContent(
            prompt=body.prompt,
            status=out.status,
            metadata=AgentMetadata(
                model=getattr(agent.llm, "name", None),
                tools=[c["tool"] for c in out.tool_calls],
                last_run_at=datetime.now(UTC),
            ),
        )
        cell = repo.set_cell(body.sheet_id, ref, content, value=out.result)
    return AgentRunResponse(
        result=out.result,
        status=out.status,
        tool_calls=out.tool_calls,
        trace=out.trace,
        cell=cell,
    )
