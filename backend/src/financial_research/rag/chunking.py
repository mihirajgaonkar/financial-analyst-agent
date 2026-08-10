from financial_research.rag.filings import FilingSection


def chunk_sections(sections: list[FilingSection], chunk_size: int = 1800, overlap: int = 200) -> list[dict]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive.")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size.")

    chunks: list[dict] = []
    for section in sections:
        text = section.text.strip()
        if not text:
            continue
        start = 0
        chunk_index = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append({"section": section.section, "chunk_index": chunk_index, "text": text[start:end].strip()})
            if end == len(text):
                break
            start = end - overlap
            chunk_index += 1
    return chunks
