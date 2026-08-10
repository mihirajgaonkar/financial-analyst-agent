from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from financial_research.api.routes.chat import router as chat_router
from financial_research.api.routes.companies import router as companies_router
from financial_research.api.routes.health import router as health_router
from financial_research.api.routes.research import router as research_router
from financial_research.config.settings import get_settings
from financial_research.middleware import RequestLoggingMiddleware, register_error_handlers


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(research_router)
    app.include_router(companies_router)
    app.include_router(chat_router)
    register_error_handlers(app)
    return app


app = create_app()
