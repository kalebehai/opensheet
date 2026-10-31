# Prompt: Write a Python agent using LangGraph that interprets natural language
# instructions from a cell, executes necessary tools (like web search), and
# returns the formatted result.
"""Cell agent.

Structured as a LangGraph-style state machine (plan -> act -> respond -> verify)
but implemented with a tiny local graph runner so the scaffold has no hard
dependency on langgraph. Swapping in `langgraph.graph.StateGraph` should only
touch `_build_graph`.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypedDict

from .llm import LLMClient, LLMMessage, StubLLM
from .tools import ToolRegistry, default_registry

END = "__end__"


class AgentState(TypedDict, total=False):
    prompt: str
    context: dict[str, Any]
    planned_tools: list[str]
    messages: list[LLMMessage]
    tool_calls: list[dict[str, str]]
    result: str
    status: str  # mirrors AgentStatus in app.models
    trace: list[str]


Node = Callable[[AgentState], AgentState]


class MiniGraph:
    """Minimal stand-in for langgraph's StateGraph: named nodes + conditional edges."""

    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.edges: dict[str, Callable[[AgentState], str]] = {}
        self.entry: str | None = None

    def add_node(self, name: str, fn: Node) -> None:
        self.nodes[name] = fn

    def add_edge(self, src: str, dst: str) -> None:
        self.edges[src] = lambda _s, dst=dst: dst

    def add_conditional_edges(self, src: str, router: Callable[[AgentState], str]) -> None:
        self.edges[src] = router

    def set_entry_point(self, name: str) -> None:
        self.entry = name

    def invoke(self, state: AgentState, max_steps: int = 16) -> AgentState:
        current = self.entry
        for _ in range(max_steps):
            if current is None or current == END:
                return state
            state = self.nodes[current](state)
            state.setdefault("trace", []).append(current)
            current = self.edges.get(current, lambda _s: END)(state)
        raise RuntimeError("agent graph exceeded max_steps")


@dataclass
class AgentResult:
    result: str
    status: str
    tool_calls: list[dict[str, str]] = field(default_factory=list)
    trace: list[str] = field(default_factory=list)


class CellAgent:
    def __init__(self, llm: LLMClient | None = None, tools: ToolRegistry | None = None):
        self.llm = llm or StubLLM()
        self.tools = tools or default_registry()
        self.graph = self._build_graph()

    def run(self, prompt: str, context: dict[str, Any] | None = None) -> AgentResult:
        state = self.graph.invoke(
            AgentState(prompt=prompt, context=context or {}, messages=[], tool_calls=[])
        )
        return AgentResult(
            result=state.get("result", ""),
            status=state.get("status", "error"),
            tool_calls=state.get("tool_calls", []),
            trace=state.get("trace", []),
        )

    # -- graph ---------------------------------------------------------------

    def _build_graph(self) -> MiniGraph:
        g = MiniGraph()
        g.add_node("plan", self._plan)
        g.add_node("act", self._act)
        g.add_node("respond", self._respond)
        g.add_node("verify", self._verify)
        g.set_entry_point("plan")
        g.add_conditional_edges("plan", lambda s: "act" if s["planned_tools"] else "respond")
        g.add_edge("act", "respond")
        g.add_edge("respond", "verify")
        return g

    def _plan(self, state: AgentState) -> AgentState:
        # TODO: let the LLM choose tools via function calling.
        state["planned_tools"] = [t.name for t in self.tools.match(state["prompt"])]
        state["status"] = "thinking"
        ctx = ", ".join(f"{k}={v}" for k, v in state["context"].items())
        system = "You fill a single spreadsheet cell. Reply with the value only."
        state["messages"] = [LLMMessage("system", system + (f" Context: {ctx}" if ctx else ""))]
        return state

    def _act(self, state: AgentState) -> AgentState:
        for name in state["planned_tools"]:
            arg = _tool_argument(name, state["prompt"])
            output = self.tools.get(name)(arg)
            state["tool_calls"].append({"tool": name, "input": arg, "output": output})
            state["messages"].append(LLMMessage("tool", f"{name}: {output}"))
        return state

    def _respond(self, state: AgentState) -> AgentState:
        calc = next((c for c in state["tool_calls"] if c["tool"] == "calculator"), None)
        if calc and not calc["output"].startswith("error"):
            state["result"] = calc["output"]  # exact answers skip the LLM
        else:
            state["messages"].append(LLMMessage("user", state["prompt"]))
            state["result"] = self.llm.complete(state["messages"])
        return state

    def _verify(self, state: AgentState) -> AgentState:
        # TODO: a second-pass check (self-consistency / citation check) before "verified".
        state["status"] = "verified" if state.get("result") else "error"
        return state


def _tool_argument(tool: str, prompt: str) -> str:
    if tool == "calculator":
        match = re.search(r"[-+*/().\d\s^]{3,}", prompt)
        return match.group(0).replace("^", "**").strip() if match else prompt
    return prompt
