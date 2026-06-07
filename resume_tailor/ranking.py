from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

from resume_tailor.models import BaseItem
from resume_tailor.text import keyword_set

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
FALLBACK_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class Embedder(Protocol):
    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        ...


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is required for ranking. Install project dependencies first."
            ) from exc

        try:
            self.model = SentenceTransformer(model_name)
            self.model_name = model_name
        except Exception:
            if model_name == FALLBACK_MODEL:
                raise
            self.model = SentenceTransformer(FALLBACK_MODEL)
            self.model_name = FALLBACK_MODEL

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        vectors = self.model.encode(list(texts), normalize_embeddings=True)
        return [list(map(float, vector)) for vector in vectors]


class CachedEmbedder:
    def __init__(self, embedder: SentenceTransformerEmbedder, cache_path: Path | None = None) -> None:
        self.embedder = embedder
        cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
        self.cache_path = cache_path or cache_root / "resume-tailor" / "embeddings.json"
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        if self.cache_path.exists():
            try:
                self.cache = json.loads(self.cache_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self.cache = {}
        else:
            self.cache = {}

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        keys = [self._key(text) for text in texts]
        missing = [text for text, key in zip(texts, keys, strict=True) if key not in self.cache]
        if missing:
            vectors = self.embedder.encode(missing)
            for text, vector in zip(missing, vectors, strict=True):
                self.cache[self._key(text)] = vector
            self.cache_path.write_text(json.dumps(self.cache), encoding="utf-8")
        return [self.cache[key] for key in keys]

    def _key(self, text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"{self.embedder.model_name}:{digest}"


@dataclass(frozen=True)
class RankedItem:
    item: BaseItem
    score: float
    semantic_score: float
    keyword_score: float
    index: int


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    denom = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    if denom == 0:
        return 0.0
    return sum(x * y for x, y in zip(a, b, strict=True)) / denom


def rank_items(
    job_text: str,
    items: Sequence[BaseItem],
    embedder: Embedder,
    semantic_weight: float = 0.80,
    keyword_weight: float = 0.20,
) -> list[RankedItem]:
    if not items:
        return []

    rank_texts = [item.text_for_rank() for item in items]
    vectors = embedder.encode([job_text, *rank_texts])
    job_vector, item_vectors = vectors[0], vectors[1:]
    job_keywords = keyword_set(job_text)

    ranked = []
    for index, (item, vector, text) in enumerate(zip(items, item_vectors, rank_texts, strict=True)):
        semantic = max(0.0, cosine(job_vector, vector))
        item_keywords = keyword_set(text)
        keyword = len(job_keywords & item_keywords) / max(1, len(item_keywords))
        score = semantic_weight * semantic + keyword_weight * keyword
        ranked.append(RankedItem(item, score, semantic, keyword, index))

    return sorted(ranked, key=lambda r: (r.score, -r.index), reverse=True)
