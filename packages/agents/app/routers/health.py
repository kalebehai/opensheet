from fastapi import APIRouter

from ..deps import llm_client

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "llm": getattr(llm_client(), "name", "custom")}
