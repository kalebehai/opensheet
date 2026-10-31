from fastapi import APIRouter, Depends, HTTPException, Response, status

from ..models import Cell, CellUpdate, Sheet, SheetCreate, SheetUpdate
from ..repository import SheetRepository, get_repository, normalize_ref, ref_in_bounds

router = APIRouter(prefix="/sheets", tags=["sheets"])


def _get_or_404(repo: SheetRepository, sheet_id: str) -> Sheet:
    sheet = repo.get(sheet_id)
    if sheet is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "sheet not found")
    return sheet


@router.get("", response_model=list[Sheet])
def list_sheets(repo: SheetRepository = Depends(get_repository)):
    return repo.list()


@router.post("", response_model=Sheet, status_code=status.HTTP_201_CREATED)
def create_sheet(body: SheetCreate, repo: SheetRepository = Depends(get_repository)):
    return repo.create(body)


@router.get("/{sheet_id}", response_model=Sheet)
def get_sheet(sheet_id: str, repo: SheetRepository = Depends(get_repository)):
    return _get_or_404(repo, sheet_id)


@router.patch("/{sheet_id}", response_model=Sheet)
def update_sheet(sheet_id: str, body: SheetUpdate, repo: SheetRepository = Depends(get_repository)):
    sheet = repo.update(sheet_id, body)
    if sheet is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "sheet not found")
    return sheet


@router.delete("/{sheet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sheet(sheet_id: str, repo: SheetRepository = Depends(get_repository)):
    if not repo.delete(sheet_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "sheet not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{sheet_id}/cells/{ref}", response_model=Cell)
def update_cell(
    sheet_id: str, ref: str, body: CellUpdate, repo: SheetRepository = Depends(get_repository)
):
    sheet = _get_or_404(repo, sheet_id)
    norm = normalize_ref(ref)
    if norm is None or not ref_in_bounds(norm, sheet):
        raise HTTPException(422, f"invalid cell ref: {ref}")
    return repo.set_cell(sheet_id, norm, body.content)
