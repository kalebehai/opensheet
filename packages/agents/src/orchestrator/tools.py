"""Tool registry for cell agents."""

from __future__ import annotations

import ast
import operator
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    fn: Callable[[str], str]
    # Lowercase keywords that make the planner pick this tool. A real planner
    # would let the LLM choose via function calling instead.
    triggers: tuple[str, ...] = ()

    def __call__(self, arg: str) -> str:
        return self.fn(arg)


@dataclass
class ToolRegistry:
    _tools: dict[str, Tool] = field(default_factory=dict)

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        return self._tools[name]

    def names(self) -> list[str]:
        return sorted(self._tools)

    def match(self, prompt: str) -> list[Tool]:
        text = prompt.lower()
        return [t for t in self._tools.values() if any(k in text for k in t.triggers)]


def web_search(query: str) -> str:
    # TODO: call a real search API (Tavily, Brave, SerpAPI...) behind a key from .env.
    return f"no live search configured for {query!r}"


_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def calculator(expr: str) -> str:
    """Safely evaluate a pure arithmetic expression."""

    def ev(node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.operand))
        raise ValueError("unsupported expression")

    try:
        result = ev(ast.parse(expr.strip(), mode="eval").body)
    except (SyntaxError, ValueError, ZeroDivisionError) as exc:
        return f"error: {exc}"
    return str(int(result) if float(result).is_integer() else result)


def default_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(
        Tool("web_search", "Search the web for current facts.", web_search,
             ("search", "find", "current", "latest", "price", "look up"))
    )
    reg.register(
        Tool("calculator", "Evaluate an arithmetic expression.", calculator,
             ("calculate", "compute", "what is"))
    )
    return reg
