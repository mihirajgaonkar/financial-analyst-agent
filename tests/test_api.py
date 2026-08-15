import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from financial_research.api.app import create_app
from financial_research.api.job_store import job_store
from financial_research.schemas.company import CompanyInfo
from financial_research.schemas.reports import ResearchReport


def test_health_endpoint() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_research_job_lifecycle(monkeypatch) -> None:
    from financial_research.api.routes import research as research_route

    def fake_run_research(ticker: str, question: str, job_id: str | None = None) -> ResearchReport:
        return ResearchReport(ticker=ticker.upper(), company_name="Microsoft", executive_summary=question)

    monkeypatch.setattr(research_route, "run_research", fake_run_research)
    client = TestClient(create_app())

    created = client.post("/research", json={"ticker": "msft", "question": "Analyze fundamentals."})
    assert created.status_code == 200
    job_id = created.json()["job_id"]

    fetched = client.get(f"/research/{job_id}")
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "complete"
    assert fetched.json()["report"]["ticker"] == "MSFT"


def test_chat_and_thread(monkeypatch) -> None:
    from financial_research.api.routes import research as research_route

    monkeypatch.setattr(
        research_route,
        "run_research",
        lambda ticker, question: ResearchReport(ticker=ticker.upper(), company_name=ticker.upper(), executive_summary=question),
    )
    client = TestClient(create_app())

    chat = client.post("/chat", json={"ticker": "AAPL", "question": "Analyze Apple."})
    assert chat.status_code == 200
    thread_id = chat.json()["thread_id"]

    thread = client.get(f"/threads/{thread_id}")
    assert thread.status_code == 200
    assert thread.json()["jobs"][0]["ticker"] == "AAPL"


def test_company_endpoint(monkeypatch) -> None:
    from financial_research.api.routes import companies as companies_route

    monkeypatch.setattr(
        companies_route,
        "get_company",
        lambda ticker: CompanyInfo(ticker=ticker.upper(), cik="0000320193", name="Apple Inc."),
    )
    client = TestClient(create_app())
    response = client.get("/companies/aapl")
    assert response.status_code == 200
    assert response.json()["company"]["ticker"] == "AAPL"


def test_streaming_research_endpoint(monkeypatch) -> None:
    from financial_research.api.routes import research as research_route

    monkeypatch.setattr(
        research_route,
        "stream_research_events",
        lambda ticker, question: iter([("research_started", "start"), ("finished", "{}")]),
    )
    client = TestClient(create_app())
    response = client.post("/research", json={"ticker": "MSFT", "question": "Analyze.", "stream": True})
    assert response.status_code == 200
    assert "event: research_started" in response.text
    assert "event: finished" in response.text
