from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from financial_research.services.exceptions import FinancialResearchError


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(FinancialResearchError)
    async def financial_research_error_handler(request: Request, exc: FinancialResearchError):
        return JSONResponse(status_code=400, content={"detail": str(exc), "path": request.url.path})

    @app.exception_handler(RuntimeError)
    async def runtime_error_handler(request: Request, exc: RuntimeError):
        return JSONResponse(status_code=500, content={"detail": str(exc), "path": request.url.path})
