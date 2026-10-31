"""LLM interface. Everything that talks to a model goes through `LLMClient`.

The default `StubLLM` is deterministic and offline so the service and tests run
without API keys. Set OPENSHEET_LLM_PROVIDER to plug in a real provider.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol


@dataclass
class LLMMessage:
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str


class LLMClient(Protocol):
    def complete(self, messages: list[LLMMessage], *, max_tokens: int = 512) -> str: ...


class StubLLM:
    """Echoes a short, predictable answer built from the last user message."""

    name = "stub"

    def complete(self, messages: list[LLMMessage], *, max_tokens: int = 512) -> str:
        last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        tool_notes = [m.content for m in messages if m.role == "tool"]
        answer = f"[stub] {last_user.strip()}"
        if tool_notes:
            answer += f" (using: {'; '.join(tool_notes)})"
        return answer[: max_tokens * 4]


def get_llm() -> LLMClient:
    provider = os.getenv("OPENSHEET_LLM_PROVIDER", "stub").lower()
    if provider == "stub":
        return StubLLM()
    # TODO: add real providers (e.g. Anthropic via ANTHROPIC_API_KEY) implementing LLMClient.
    raise ValueError(f"Unknown OPENSHEET_LLM_PROVIDER: {provider!r}")
