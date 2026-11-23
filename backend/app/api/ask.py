"""POST /api/kb/ask: hỏi đáp về quy chế nội bộ cho trang Tra cứu của portal (docs/07, /tools/tra-cuu).

Dùng CHÍNH hàm `app.rag.answer.ask` như tool `ask_knowledge` của knowledge-mcp, nên cùng lọc quyền (ACL theo
người hỏi, không ngoại lệ cho admin), cùng kiểm tra trích dẫn, cùng ghi audit.
Khác knowledge-mcp ở chỗ trả JSON
có cấu trúc (danh sách nguồn kèm mã tài liệu) thay vì một đoạn văn bản.
Router chỉ nhận request, tra người hỏi, gọi `ask`, đổi sang schema (theo khuôn app/api/kb.py).
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy.orm import Session

from app.api.deps import get_asker_email, get_db
from app.api.kb import CamelModel
from app.rag.acl import load_principal
from app.rag.answer import AskResult, ask

router = APIRouter(tags=["kb"])


class AskIn(CamelModel):
    question: str = Field(min_length=1, max_length=1000)
    as_of: date | None = None  # tra theo quy định tại một ngày khác hôm nay


class CitationOut(CamelModel):
    n: int  # số [n] trong câu trả lời
    label: str  # "SVT-QC-003 – Điều 3: Số ngày phép"
    doc_id: str | None  # để portal mở đúng tài liệu; None nếu không tra được


class AskOut(CamelModel):
    answer: str
    found: bool
    citations: list[CitationOut]
    withheld: list[str]  # vị trí tài liệu Mật bạn được xem nhưng trợ lý không đọc (SVT-CS-007 Điều 5)
    as_of: date
    model: str
    latency_ms: int


def to_ask_out(r: AskResult, as_of: date) -> AskOut:
    doc_by_cite = {h.cite: h.doc_id for h in r.hits}
    return AskOut(
        answer=r.answer,
        found=r.found,
        citations=[
            CitationOut(n=i, label=c, doc_id=doc_by_cite.get(c)) for i, c in enumerate(r.citations, 1)
        ],
        withheld=r.withheld,
        as_of=as_of,
        model=r.model,
        latency_ms=r.latency_ms,
    )


# `def` thường, không `async def`: truy vấn DB, embedding và gọi LLM đều là việc đồng bộ nặng,
# FastAPI chạy trong thread pool nên không chặn event loop.
@router.post("/ask", response_model=AskOut)
def ask_endpoint(body: AskIn, email: str = Depends(get_asker_email), db: Session = Depends(get_db)) -> AskOut:
    principal = load_principal(db, email)
    if principal is None:
        raise HTTPException(
            403, "Tài khoản của bạn chưa có trong danh bạ nhân sự nên không tra cứu được tài liệu."
        )
    if not principal.active:
        raise HTTPException(
            403, "Tài khoản nhân sự của bạn không còn hoạt động nên không tra cứu được tài liệu nội bộ."
        )
    as_of = body.as_of or date.today()
    return to_ask_out(ask(db, body.question.strip(), principal, as_of=as_of), as_of)
