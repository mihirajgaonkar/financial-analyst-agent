from datetime import date

from pydantic import BaseModel


class SECFiling(BaseModel):
    cik: str
    accession_number: str
    form: str
    filing_date: date
    report_date: date | None = None
    primary_document: str | None = None
    url: str | None = None
