from financial_research.api import service
from financial_research.config.settings import Settings
from financial_research.schemas.reports import ResearchReport


def test_run_research_skips_database_persistence_by_default(monkeypatch, tmp_path) -> None:
    report = ResearchReport(ticker="MSFT", company_name="Microsoft", executive_summary="Done.")

    monkeypatch.setattr(
        service,
        "run_research_graph",
        lambda ticker, research_question: {"final_report": report, "messages": [], "tool_results": []},
    )
    monkeypatch.setattr(
        service,
        "get_settings",
        lambda: Settings(
            debug_reports_enabled=False,
            file_storage_enabled=True,
            file_storage_dir=str(tmp_path),
            database_persistence_enabled=False,
        ),
    )

    def fail_if_called(*args, **kwargs) -> None:
        raise AssertionError("database persistence should be skipped by default")

    monkeypatch.setattr(service, "persist_research_run", fail_if_called)

    result = service.run_research("msft", "Analyze.")

    assert result.ticker == "MSFT"
    assert next(tmp_path.glob("MSFT_*")).is_dir()
