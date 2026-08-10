import math
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class VectorSearchResult:
    text: str
    metadata: dict
    score: float


class VectorStore(Protocol):
    def add_texts(self, texts: list[str], embeddings: list[list[float]], metadatas: list[dict]) -> None: ...

    def similarity_search(self, query_embedding: list[float], limit: int = 5, filters: dict | None = None) -> list[VectorSearchResult]: ...


class InMemoryVectorStore:
    def __init__(self) -> None:
        self._records: list[tuple[str, list[float], dict]] = []

    def add_texts(self, texts: list[str], embeddings: list[list[float]], metadatas: list[dict]) -> None:
        for text, embedding, metadata in zip(texts, embeddings, metadatas, strict=True):
            self._records.append((text, embedding, metadata))

    def similarity_search(self, query_embedding: list[float], limit: int = 5, filters: dict | None = None) -> list[VectorSearchResult]:
        results: list[VectorSearchResult] = []
        for text, embedding, metadata in self._records:
            if filters and any(metadata.get(key) != value for key, value in filters.items()):
                continue
            results.append(VectorSearchResult(text=text, metadata=metadata, score=_cosine_similarity(query_embedding, embedding)))
        return sorted(results, key=lambda result: result.score, reverse=True)[:limit]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Vectors must have the same dimensions.")
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)
