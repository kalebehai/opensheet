from fastapi import APIRouter, Depends

from orchestrator import LLMClient
from orchestrator.formula_translator import translate

from ..deps import llm_client
from ..models import FormulaTranslateRequest, FormulaTranslateResponse

router = APIRouter(prefix="/formulas", tags=["formulas"])


@router.post("/translate", response_model=FormulaTranslateResponse)
def translate_formula(body: FormulaTranslateRequest, llm: LLMClient = Depends(llm_client)):
    t = translate(body.text, llm)
    return FormulaTranslateResponse(**t.__dict__)
