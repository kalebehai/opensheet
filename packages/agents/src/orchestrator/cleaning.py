"""Column-level anomaly scanner used by autonomous data cleaning."""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from typing import Any

_DATE_FORMATS = {
    "iso": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    "slash": re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}$"),
    "dot": re.compile(r"^\d{1,2}\.\d{1,2}\.\d{2,4}$"),
}


@dataclass
class Anomaly:
    column: str
    row: int | None  # 0-based data row, None for column-level issues
    kind: str
    message: str
    suggestion: str | None = None


def _as_number(v: Any) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, int | float):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.replace(",", "").strip())
        except ValueError:
            return None
    return None


def scan(headers: list[str], rows: list[list[Any]]) -> list[Anomaly]:
    out: list[Anomaly] = []
    seen: dict[tuple, int] = {}
    for i, row in enumerate(rows):
        key = tuple(row)
        if key in seen:
            out.append(Anomaly("*", i, "duplicate_row", f"Row {i} duplicates row {seen[key]}",
                               "Remove duplicate"))
        else:
            seen[key] = i

    for c, name in enumerate(headers):
        col = [row[c] if c < len(row) else None for row in rows]
        for i, v in enumerate(col):
            if v is None or (isinstance(v, str) and not v.strip()):
                out.append(Anomaly(name, i, "missing", "Empty value"))
            elif isinstance(v, str) and v != v.strip():
                out.append(Anomaly(name, i, "whitespace", "Leading/trailing whitespace",
                                   v.strip()))

        present = [v for v in col if v not in (None, "")]
        nums = [(i, _as_number(v)) for i, v in enumerate(col) if v not in (None, "")]
        numeric = [(i, n) for i, n in nums if n is not None]
        if present and len(numeric) / len(present) >= 0.8:
            for i, n in nums:
                if n is None:
                    out.append(Anomaly(name, i, "type_mismatch",
                                       f"Non-numeric value {col[i]!r} in numeric column"))
            values = [n for _, n in numeric]
            if len(values) >= 4:
                q1, _, q3 = statistics.quantiles(values, n=4)
                lo, hi = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
                for i, n in numeric:
                    if n < lo or n > hi:
                        out.append(Anomaly(name, i, "outlier",
                                           f"{n:g} is outside [{lo:g}, {hi:g}]"))

        fmts = {f for v in present if isinstance(v, str)
                for f, rx in _DATE_FORMATS.items() if rx.match(v.strip())}
        if len(fmts) > 1:
            out.append(Anomaly(name, None, "inconsistent_dates",
                               f"Mixed date formats: {', '.join(sorted(fmts))}",
                               "Normalize to ISO 8601 (YYYY-MM-DD)"))
    # TODO: LLM pass for semantic issues (e.g. "N/A" vs "unknown", unit mismatches).
    return out
