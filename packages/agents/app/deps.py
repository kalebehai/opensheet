from functools import lru_cache

from orchestrator import CellAgent, LLMClient, get_llm


@lru_cache
def llm_client() -> LLMClient:
    return get_llm()


def cell_agent() -> CellAgent:
    return CellAgent(llm=llm_client())
