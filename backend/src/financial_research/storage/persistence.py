from __future__ import annotations

import logging
import json
from pathlib import Path
from typing import Any

from financial_research.config.settings import get_settings
from financial_research.schemas.reports import ResearchReport
from financial_research.storage.database import create_session_factory
from financial_research.storage.repositories import (
    FinancialMetricRepository,
    GraphTraceRepository,
    ProviderResponseRepository,
    ReportRepository,
    ResearchJobRepository,
    SourceRepository,
)

logger = logging.getLogger(__name__)


def persist_research_run(
    *,
    ticker: str,
    question: str,
    state: dict[str, Any],
    report: ResearchReport,
    external_responses: list[dict[str, Any]],
    file_archive_dir: Path | None = None,
) -> None:
    """Persist completed research artifacts without affecting the API response path."""
    settings = get_settings()
    factory = create_session_factory()
    with factory() as session:
        try:
            job_repo = ResearchJobRepository(session)
            job = job_repo.create(ticker, question)
            ReportRepository(session).save(report, job_id=job.id)
            FinancialMetricRepository(session).save_many(ticker, report.calculated_metrics)
            SourceRepository(session).save_many(report.sources)
            GraphTraceRepository(session).save(ticker, state, job_id=job.id)
            ProviderResponseRepository(session).save_many(
                external_responses,
                job_id=job.id,
                file_paths=_provider_file_paths(file_archive_dir),
                store_payloads=settings.database_store_raw_provider_payloads,
            )
            job_repo.mark_complete(job)
            session.commit()
        except Exception:
            session.rollback()
            logger.exception("Failed to persist research run for %s.", ticker.upper())
            raise


def _provider_file_paths(file_archive_dir: Path | None) -> list[str | None] | None:
    if file_archive_dir is None:
        return None
    index_path = file_archive_dir / "provider_responses_index.json"
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return [str(file_archive_dir / item["file"]) for item in index if "file" in item]
