from fastapi import APIRouter, HTTPException

from financial_research.api.schemas import CompanyResponse
from financial_research.api.service import get_company

router = APIRouter(tags=["companies"])


@router.get("/companies/{ticker}", response_model=CompanyResponse)
def get_company_route(ticker: str) -> CompanyResponse:
    try:
        company = get_company(ticker)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CompanyResponse(company=company, cik=company.cik)
