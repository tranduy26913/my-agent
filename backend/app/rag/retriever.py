"""Hybrid retrieval cho kho tri thức có phân quyền và hiệu lực.

Ba nhánh xếp hạng, gộp bằng Reciprocal Rank Fusion (RRF):
  1. vector   : ngữ nghĩa ("lấy vợ" ≈ "kết hôn")
  2. keyword  : full-text không dấu + từ điển viết tắt (số liệu, tên riêng, "CTP")
  3. explicit : tài liệu được nêu ĐÍCH DANH bằng số hiệu/mã ("12/2023/QĐ-SVT")

Bộ lọc nằm TRONG SQL của từng nhánh (lọc trước, không lọc sau):
  - ACL (app/rag/acl.py)          -> tài liệu không được phép không bao giờ rời DB
  - không bị cách ly (quarantined)
  - còn hiệu lực tại ngày `as_of`  -> bản quy chế 2024 không lẫn vào câu trả lời năm 2026
Ngoại lệ hiệu lực: tài liệu được nêu đích danh (nhánh 3) vẫn lấy dù đã hết hiệu lực, kèm văn bản
thay thế nó -> trả lời được "QĐ 12/2023 còn hiệu lực không?". ACL thì KHÔNG có ngoại lệ.
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.rag.acl import Principal, acl_sql
from app.rag.embeddings import embed_query
from app.rag.query import QueryPlan, analyze


@dataclass
class Hit:
    chunk_id: int
    doc_id: str
    so_hieu: str | None
    title: str
    section: str
    content: str
    score: float
    classification: str
    effective_from: date | None
    effective_to: date | None
    superseded_by: str | None
    in_force: bool  # còn hiệu lực tại as_of?

    @property
    def is_secret(self) -> bool:
        return self.classification == "Mat"

    @property
    def cite(self) -> str:
        return f"{self.doc_id}{' – ' + self.section if self.section else ''}"


def rrf_fuse(ranked_lists: list[list[int]], k: int = 60) -> list[tuple[int, float]]:
    """score(d) = Σ 1/(k + rank). Chỉ dùng THỨ HẠNG -> không phải chuẩn hóa điểm cosine với ts_rank."""
    scores: dict[int, float] = {}
    for ranked in ranked_lists:
        for rank, item in enumerate(ranked, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def in_force_sql(as_of: date):
    from app.models import Document

    return and_(
        or_(Document.effective_from.is_(None), Document.effective_from <= as_of),
        or_(Document.effective_to.is_(None), Document.effective_to > as_of),
    )


def _explicit_doc_ids(db: Session, plan: QueryPlan, p: Principal) -> list[int]:
    """Tài liệu nêu đích danh + văn bản thay thế/bị thay thế của chúng (vẫn qua ACL)."""
    from app.models import Document

    if not plan.doc_refs:
        return []
    named = db.execute(
        select(Document.id, Document.superseded_by, Document.supersedes).where(
            acl_sql(p),
            or_(
                func.upper(Document.so_hieu).in_(plan.doc_refs),
                func.upper(Document.doc_id).in_(plan.doc_refs),
            ),
        )
    ).all()
    related = {x for r in named for x in (r.superseded_by, r.supersedes) if x}
    ids = [r.id for r in named]
    if related:
        ids += db.execute(select(Document.id).where(acl_sql(p), Document.doc_id.in_(related))).scalars().all()
    return list(dict.fromkeys(ids))


def retrieve(
    db: Session, question: str, p: Principal, as_of: date | None = None, top_k: int | None = None
) -> list[Hit]:
    from app.models import Chunk, Document

    as_of = as_of or date.today()
    top_k = top_k or settings.rag_top_k
    n = settings.rag_candidates
    plan = analyze(question)
    explicit = _explicit_doc_ids(db, plan, p)

    base = and_(acl_sql(p), Document.quarantined.is_(False))
    time_ok = or_(in_force_sql(as_of), Document.id.in_(explicit)) if explicit else in_force_sql(as_of)
    qvec = embed_query(question)

    vec = db.execute(
        select(Chunk.id).join(Document).where(base, time_ok)
        .order_by(Chunk.embedding.cosine_distance(qvec)).limit(n)
    ).scalars().all()

    kw: list[int] = []
    if plan.tsquery:
        tsq = func.to_tsquery("simple", plan.tsquery)
        kw = db.execute(
            select(Chunk.id).join(Document).where(base, time_ok, Chunk.tsv.op("@@")(tsq))
            .order_by(func.ts_rank_cd(Chunk.tsv, tsq).desc()).limit(n)
        ).scalars().all()

    exp: list[int] = []
    if explicit:
        exp = db.execute(
            select(Chunk.id).join(Document).where(base, Document.id.in_(explicit))
            .order_by(Chunk.embedding.cosine_distance(qvec)).limit(top_k)
        ).scalars().all()

    fused = rrf_fuse([list(vec), list(kw), list(exp)])[:top_k]
    if not fused:
        return []
    ids = [cid for cid, _ in fused]
    rows = {
        r.id: r
        for r in db.execute(
            select(
                Chunk.id, Chunk.section, Chunk.content, Document.doc_id, Document.so_hieu, Document.title,
                Document.classification, Document.effective_from, Document.effective_to,
                Document.superseded_by,
            ).join(Document).where(Chunk.id.in_(ids))
        ).all()
    }
    hits = []
    for cid, score in fused:
        r = rows[cid]
        alive = (r.effective_from is None or r.effective_from <= as_of) and (
            r.effective_to is None or r.effective_to > as_of
        )
        hits.append(Hit(cid, r.doc_id, r.so_hieu, r.title, r.section, r.content, score, r.classification,
                        r.effective_from, r.effective_to, r.superseded_by, alive))
    return hits


def format_hits(hits: list[Hit]) -> str:
    """Dạng văn bản đơn giản cho agent tool / debug CLI."""
    if not hits:
        return "Không tìm thấy tài liệu phù hợp (hoặc bạn không có quyền truy cập)."
    return "\n\n---\n\n".join(f"[{h.cite}]\n{h.content}" for h in hits)
