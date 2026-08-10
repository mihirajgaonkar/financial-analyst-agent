from financial_research.rag.embeddings import EmbeddingProvider
from financial_research.rag.filings import FilingDocument, prepare_filing_chunks
from financial_research.rag.vector_store import VectorSearchResult, VectorStore


class FilingRAGPipeline:
    def __init__(self, embedding_provider: EmbeddingProvider, vector_store: VectorStore) -> None:
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store

    def index_filing(self, document: FilingDocument) -> list[dict]:
        chunks = prepare_filing_chunks(document)
        texts = [chunk["text"] for chunk in chunks]
        embeddings = self.embedding_provider.embed_texts(texts)
        metadatas = [{key: value for key, value in chunk.items() if key != "text"} for chunk in chunks]
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            chunk["embedding"] = embedding
        self.vector_store.add_texts(texts, embeddings, metadatas)
        return chunks

    def retrieve(self, query: str, ticker: str | None = None, section: str | None = None, limit: int = 5) -> list[VectorSearchResult]:
        filters = {}
        if ticker:
            filters["ticker"] = ticker.upper()
        if section:
            filters["section"] = section
        query_embedding = self.embedding_provider.embed_query(query)
        return self.vector_store.similarity_search(query_embedding, limit=limit, filters=filters or None)
