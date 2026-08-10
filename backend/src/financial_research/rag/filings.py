import re
from dataclasses import dataclass


@dataclass(frozen=True)
class FilingDocument:
    ticker: str
    cik: str
    accession_number: str
    filing_type: str
    text: str
    filing_date: str | None = None
    fiscal_period: str | None = None
    source_url: str | None = None


@dataclass(frozen=True)
class FilingSection:
    section: str
    text: str


SECTION_PATTERNS = {
    "business": re.compile(r"\bitem\s+1\.\s+business\b", re.IGNORECASE),
    "risk_factors": re.compile(r"\bitem\s+1a\.\s+risk\s+factors\b", re.IGNORECASE),
    "mda": re.compile(r"\bitem\s+7\.\s+management'?s\s+discussion\s+and\s+analysis\b", re.IGNORECASE),
    "financial_statements": re.compile(r"\bitem\s+8\.\s+financial\s+statements\b", re.IGNORECASE),
    "controls": re.compile(r"\bitem\s+9a\.\s+controls\s+and\s+procedures\b", re.IGNORECASE),
}


def parse_filing_sections(text: str) -> list[FilingSection]:
    normalized = normalize_filing_text(text)
    matches: list[tuple[int, str]] = []
    for section, pattern in SECTION_PATTERNS.items():
        match = pattern.search(normalized)
        if match:
            matches.append((match.start(), section))
    if not matches:
        return [FilingSection(section="full_text", text=normalized)]
    matches.sort(key=lambda item: item[0])
    sections: list[FilingSection] = []
    for index, (start, section) in enumerate(matches):
        end = matches[index + 1][0] if index + 1 < len(matches) else len(normalized)
        sections.append(FilingSection(section=section, text=normalized[start:end].strip()))
    return sections


def prepare_filing_chunks(document: FilingDocument, chunk_size: int = 1800, overlap: int = 200) -> list[dict]:
    from financial_research.rag.chunking import chunk_sections

    overlap = min(overlap, max(chunk_size - 1, 0))
    chunks = chunk_sections(parse_filing_sections(document.text), chunk_size=chunk_size, overlap=overlap)
    return [
        {
            "ticker": document.ticker.upper(),
            "cik": document.cik,
            "accession_number": document.accession_number,
            "filing_type": document.filing_type,
            "filing_date": document.filing_date,
            "fiscal_period": document.fiscal_period,
            "section": chunk["section"],
            "chunk_index": chunk["chunk_index"],
            "text": chunk["text"],
            "source_url": document.source_url,
            "embedding": None,
        }
        for chunk in chunks
    ]


def normalize_filing_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
