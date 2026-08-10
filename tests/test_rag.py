from financial_research.rag.chunking import chunk_sections
from financial_research.rag.embeddings import DeterministicHashEmbeddingProvider
from financial_research.rag.filings import FilingDocument, FilingSection, parse_filing_sections, prepare_filing_chunks
from financial_research.rag.pipeline import FilingRAGPipeline
from financial_research.rag.vector_store import InMemoryVectorStore


def test_parse_filing_sections_uses_sec_item_boundaries() -> None:
    sections = parse_filing_sections(
        """
        Item 1. Business We sell software.
        Item 1A. Risk Factors Demand may decline.
        Item 7. Management's Discussion and Analysis Revenue increased.
        """
    )
    assert [section.section for section in sections] == ["business", "risk_factors", "mda"]
    assert "Demand may decline" in sections[1].text


def test_chunk_sections_preserves_section_metadata() -> None:
    chunks = chunk_sections([FilingSection(section="risk_factors", text="abcdef")], chunk_size=4, overlap=1)
    assert chunks == [
        {"section": "risk_factors", "chunk_index": 0, "text": "abcd"},
        {"section": "risk_factors", "chunk_index": 1, "text": "def"},
    ]


def test_prepare_filing_chunks_includes_sec_metadata() -> None:
    document = FilingDocument(
        ticker="aapl",
        cik="0000320193",
        accession_number="abc",
        filing_type="10-K",
        filing_date="2025-10-31",
        fiscal_period="FY2025",
        source_url="https://www.sec.gov/filing",
        text="Item 1A. Risk Factors Supply constraints may affect results.",
    )
    chunks = prepare_filing_chunks(document, chunk_size=100)
    assert chunks[0]["ticker"] == "AAPL"
    assert chunks[0]["section"] == "risk_factors"
    assert chunks[0]["source_url"] == "https://www.sec.gov/filing"


def test_filing_rag_pipeline_indexes_and_retrieves_by_section() -> None:
    pipeline = FilingRAGPipeline(DeterministicHashEmbeddingProvider(), InMemoryVectorStore())
    document = FilingDocument(
        ticker="MSFT",
        cik="0000789019",
        accession_number="xyz",
        filing_type="10-K",
        text="Item 1A. Risk Factors Cybersecurity risk remains material. Item 7. Management's Discussion and Analysis Cloud revenue grew.",
    )
    chunks = pipeline.index_filing(document)
    results = pipeline.retrieve("cybersecurity risk", ticker="MSFT", section="risk_factors", limit=1)

    assert chunks[0]["embedding"]
    assert results[0].metadata["ticker"] == "MSFT"
    assert results[0].metadata["section"] == "risk_factors"
