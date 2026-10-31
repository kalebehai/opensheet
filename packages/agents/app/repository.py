"""In-memory sheet repository. TODO: replace with Postgres/SQLite behind the same interface."""

from __future__ import annotations

import re
from threading import Lock

from .models import Cell, CellContent, Sheet, SheetCreate, SheetUpdate, _now

_A1 = re.compile(r"^([A-Z]{1,3})([1-9]\d*)$")


def normalize_ref(ref: str) -> str | None:
    ref = ref.strip().upper()
    return ref if _A1.match(ref) else None


def ref_in_bounds(ref: str, sheet: Sheet) -> bool:
    letters, digits = _A1.match(ref).groups()  # type: ignore[union-attr]
    col = 0
    for ch in letters:
        col = col * 26 + (ord(ch) - 64)
    return col <= sheet.cols and int(digits) <= sheet.rows


class SheetRepository:
    def __init__(self) -> None:
        self._sheets: dict[str, Sheet] = {}
        self._lock = Lock()

    def list(self) -> list[Sheet]:
        return list(self._sheets.values())

    def get(self, sheet_id: str) -> Sheet | None:
        return self._sheets.get(sheet_id)

    def create(self, data: SheetCreate) -> Sheet:
        sheet = Sheet(**data.model_dump())
        with self._lock:
            self._sheets[sheet.id] = sheet
        return sheet

    def update(self, sheet_id: str, data: SheetUpdate) -> Sheet | None:
        with self._lock:
            sheet = self._sheets.get(sheet_id)
            if sheet is None:
                return None
            updated = sheet.model_copy(
                update={**data.model_dump(exclude_none=True), "updated_at": _now()}
            )
            self._sheets[sheet_id] = updated
            return updated

    def delete(self, sheet_id: str) -> bool:
        with self._lock:
            return self._sheets.pop(sheet_id, None) is not None

    def set_cell(self, sheet_id: str, ref: str, content: CellContent, value=None) -> Cell | None:
        with self._lock:
            sheet = self._sheets.get(sheet_id)
            if sheet is None:
                return None
            if value is None and content.type == "raw":
                value = content.value
            cell = Cell(ref=ref, content=content, value=value)
            sheet.cells[ref] = cell
            sheet.updated_at = _now()
            # TODO: hand dependents to the core engine (packages/core) for recalculation.
            return cell

    def clear(self) -> None:
        with self._lock:
            self._sheets.clear()


repository = SheetRepository()


def get_repository() -> SheetRepository:
    return repository
