"""Phân tích câu hỏi trước khi truy xuất (không gọi LLM -> nhanh, rẻ, tất định, dễ test).

1. Bắt số hiệu văn bản ("12/2023/QĐ-CTA") và mã tài liệu ("CTA-QC-003"): embedding xử lý chuỗi kiểu
   này rất kém, nên khớp CHÍNH XÁC trong SQL rồi đưa thành một nhánh xếp hạng riêng.
2. Mở rộng viết tắt / đồng nghĩa theo tu_dien.yaml cho nhánh full-text.
3. Dựng tsquery: OR các âm tiết có nghĩa + các cặp âm tiết liền nhau (toán tử <->) để ưu tiên cụm từ.
   Tiếng Việt viết theo âm tiết: "nghỉ phép" là 2 token; chỉ OR từng âm tiết thì "nghỉ" khớp mọi thứ.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

SO_HIEU = re.compile(r"\b\d{1,3}/\d{4}/[A-Za-zĐđ]+(?:-[A-Za-z]+)?\b")
DOC_ID = re.compile(r"\bCTA-[A-Z]{2,3}-\d{3}\b", re.IGNORECASE)

# Âm tiết hư từ (đã bỏ dấu). Bỏ khỏi tsquery để không kéo về mọi chunk có chữ "được", "không"...
STOPWORDS = set(
    "toi ban minh co duoc khong bao nhieu la thi va cua cho the nao gi may mot nhung cac de o khi ai hay "
    "voi nay do ra vao con phai tu den sao nhu ve muon can moi neu se da dang bi cung roi a u nhe "
    "lieu tai sau truoc trong ngoai len xuong vay".split()
)


def unaccent(text: str) -> str:
    """Bỏ dấu tiếng Việt, khớp với f_unaccent() phía Postgres."""
    text = text.replace("đ", "d").replace("Đ", "D")
    nfd = unicodedata.normalize("NFD", text)
    return unicodedata.normalize("NFC", "".join(c for c in nfd if unicodedata.category(c) != "Mn"))


@lru_cache
def synonyms() -> dict[str, list[str]]:
    path = Path(__file__).with_name("tu_dien.yaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {unaccent(str(k)).lower(): [unaccent(v).lower() for v in vs] for k, vs in data.items()}


@dataclass
class QueryPlan:
    text: str  # câu gốc (dùng cho vector)
    doc_refs: list[str] = field(default_factory=list)  # số hiệu / mã tài liệu, viết HOA
    expansions: list[str] = field(default_factory=list)
    tsquery: str = ""  # cú pháp to_tsquery('simple', ...)


def analyze(question: str) -> QueryPlan:
    refs = [m.upper() for m in SO_HIEU.findall(question)] + [m.upper() for m in DOC_ID.findall(question)]
    norm = unaccent(question).lower()

    expansions = []
    for key, values in synonyms().items():
        if re.search(rf"(?<!\w){re.escape(key)}(?!\w)", norm):
            expansions += values

    def useful(t: str) -> bool:
        return t not in STOPWORDS and len(t) > 1

    parts: set[str] = set()
    for phrase in [norm, *expansions]:
        toks = re.findall(r"[a-z0-9]+", phrase)
        parts.update(t for t in toks if useful(t))
        # cặp chỉ tính khi hai âm tiết THỰC SỰ liền nhau trong câu gốc
        parts.update(f"{a} <-> {b}" for a, b in zip(toks, toks[1:], strict=False) if useful(a) and useful(b))
    tsq = " | ".join(f"({p})" if "<->" in p else p for p in sorted(parts))
    return QueryPlan(question, sorted(set(refs)), expansions, tsq)
