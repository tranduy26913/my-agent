"""Embedding provider. Claude không có embedding endpoint -> dùng model mã nguồn mở chạy local
(fastembed/ONNX, CPU-friendly, hỗ trợ đa ngôn ngữ gồm tiếng Việt). Dữ liệu không rời máy chủ.
"""

import hashlib
import math
import re
from functools import lru_cache
from typing import Protocol

from app.config import settings


class Embedder(Protocol):
    dim: int

    def embed(self, texts: list[str], kind: str = "passage") -> list[list[float]]:
        """kind: "passage" khi nạp tài liệu, "query" khi embed câu hỏi."""
        ...


class FastEmbedEmbedder:
    def __init__(self, model_name: str, dim: int):
        from fastembed import TextEmbedding  # import lười: chỉ tải model khi cần

        self.model = TextEmbedding(model_name=model_name)
        self.dim = dim
        # Họ e5 được huấn luyện với tiền tố bất đối xứng: câu hỏi ngắn "query: ...", đoạn văn "passage: ...".
        # Quên tiền tố -> recall giảm rõ rệt (lỗi rất hay gặp khi đổi model embedding).
        self.asymmetric = "e5" in model_name.lower()

    def embed(self, texts: list[str], kind: str = "passage") -> list[list[float]]:
        if self.asymmetric:
            texts = [f"{kind}: {t}" for t in texts]
        return [v.tolist() for v in self.model.embed(texts)]


class HashEmbedder:
    """Bag-of-words băm vào vector cố định. KHÔNG có ngữ nghĩa - chỉ để test/CI chạy offline."""

    def __init__(self, dim: int):
        self.dim = dim

    def embed(self, texts: list[str], kind: str = "passage") -> list[list[float]]:
        out = []
        for t in texts:
            v = [0.0] * self.dim
            for tok in re.findall(r"\w+", t.lower()):
                h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
                v[h % self.dim] += 1.0
            norm = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / norm for x in v])
        return out


@lru_cache
def get_embedder() -> Embedder:
    if settings.embedding_provider == "hash":
        return HashEmbedder(settings.embedding_dim)
    return FastEmbedEmbedder(settings.embedding_model, settings.embedding_dim)


def embed_query(text: str) -> list[float]:
    return get_embedder().embed([text], kind="query")[0]


def embed_one(text: str) -> list[float]:
    return get_embedder().embed([text])[0]
