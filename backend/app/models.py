"""ORM models. Mỗi bảng phục vụ một yêu cầu trong JD:

- employees                    -> dữ liệu nhân sự + phân quyền (RBAC); đăng nhập do Zitadel lo
- leave_balances/_requests, employee_contacts -> phép năm, đơn nghỉ, số điện thoại (ADR-003, /api/hr)
- documents / chunks           -> kho tri thức nội bộ (RAG, hybrid search, ACL theo tài liệu)
- skills                       -> thư viện kỹ năng dùng chung (có duyệt)
- experiences                  -> kho kinh nghiệm agent tự tích lũy (reflection)
- conversations / messages     -> bộ nhớ ngắn hạn (lịch sử hội thoại)
- audit_logs / usage_logs      -> lưu vết + kiểm soát chi phí
- ocr_jobs                     -> job OCR bất đồng bộ (kết quả tạm, tự hết hạn)
- feedback                     -> cải tiến liên tục dựa trên phản hồi người dùng
"""

from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    Computed,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import settings
from app.db import Base

DIM = settings.embedding_dim


class Employee(Base):
    """Dữ liệu nhân sự mô phỏng (thực tế: đồng bộ từ HRM qua API)."""

    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True)
    full_name: Mapped[str] = mapped_column(String(128), index=True)
    department: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(128))
    email: Mapped[str] = mapped_column(String(128))
    manager_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    leave_balance: Mapped[float] = mapped_column(Float, default=12)  # trường nhạy cảm
    # Một người có thể giữ nhiều vai trò (CSV: "hr|manager") -> mảng, không phải 1 chuỗi
    roles: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    status: Mapped[str] = mapped_column(String(32), default="dang-lam")  # dang-lam | da-nghi-viec


class LeaveBalance(Base):
    """Số dư phép năm theo từng nhân viên (thực tế: đồng bộ từ HRM). ADR-003: `leave_balance:read:*`."""

    __tablename__ = "leave_balances"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_code: Mapped[str] = mapped_column(ForeignKey("employees.code"), index=True)
    year: Mapped[int] = mapped_column(Integer)
    entitled: Mapped[float] = mapped_column(Float, default=0)  # phép năm được hưởng
    carried_over: Mapped[float] = mapped_column(Float, default=0)  # tồn chuyển sang
    carried_expired: Mapped[float] = mapped_column(Float, default=0)  # tồn đã huỷ
    used: Mapped[float] = mapped_column(Float, default=0)
    remaining: Mapped[float] = mapped_column(Float, default=0)

    __table_args__ = (UniqueConstraint("employee_code", "year", name="uq_leave_balance_employee_year"),)


class LeaveRequest(Base):
    """Đơn nghỉ. ADR-003: `leave_request:read:*`; chưa có quyền duyệt (chỉ đọc)."""

    __tablename__ = "leave_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)  # DP-2026-0001
    employee_code: Mapped[str] = mapped_column(ForeignKey("employees.code"), index=True)
    kind: Mapped[str] = mapped_column(String(32))  # phep-nam | nghi-om-co-luong | ...
    from_date: Mapped[date] = mapped_column(Date)
    to_date: Mapped[date] = mapped_column(Date)
    days: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16))  # cho-duyet | da-duyet | tu-choi
    approver_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")  # lý do do nhân viên tự viết: dữ liệu cá nhân


class EmployeeContact(Base):
    """Số điện thoại: tách khỏi `employees` vì bị che theo người xem (ADR-003, directory:read:phone_*)."""

    __tablename__ = "employee_contacts"
    employee_code: Mapped[str] = mapped_column(ForeignKey("employees.code"), primary_key=True)
    phone: Mapped[str] = mapped_column(String(32))


class Document(Base):
    """Một văn bản trong kho tri thức. Các cột ánh xạ 1-1 với frontmatter trong data/knowledge."""

    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    doc_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # SVT-QC-003
    so_hieu: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)  # 01/2026/QĐ-SVT
    title: Mapped[str] = mapped_column(String(256))
    doc_type: Mapped[str | None] = mapped_column(String(32), nullable=True)  # quy-che | quy-trinh ...
    source: Mapped[str] = mapped_column(String(512))
    department: Mapped[str] = mapped_column(String(64), default="General")  # phòng sở hữu
    # cong-khai | phong-ban | han-che -> quy tắc xem trong app/rag/acl.py (ADR-001)
    visibility: Mapped[str] = mapped_column(String(16), default="cong-khai")
    allowed_departments: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    allowed_roles: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    classification: Mapped[str] = mapped_column(String(16), default="thuong")  # thuong | Mat
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)  # NULL = còn hiệu lực
    supersedes: Mapped[str | None] = mapped_column(String(64), nullable=True)  # doc_id bản cũ
    superseded_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    version: Mapped[str | None] = mapped_column(String(16), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), default="")  # nạp lại idempotent
    # Tài liệu bị nghi chứa chỉ dẫn độc hại -> không bao giờ được truy xuất (P2 sẽ tự gắn cờ)
    quarantined: Mapped[bool] = mapped_column(Boolean, default=False)
    uploaded_by: Mapped[str | None] = mapped_column(String(255), nullable=True)  # email người nạp (Zitadel)
    ocr_pages: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section: Mapped[str] = mapped_column(String(256), default="")  # "Chương II > Điều 5. ..." -> trích dẫn
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(DIM))
    # Full-text search cho nhánh keyword của hybrid search. 'simple' = không stemming (hợp tiếng Việt);
    # f_unaccent (tạo trong init_db) bỏ dấu -> câu hỏi gõ không dấu "nghi phep" vẫn khớp.
    tsv: Mapped[str] = mapped_column(
        TSVECTOR, Computed("to_tsvector('simple', f_unaccent(content))", persisted=True)
    )
    document: Mapped[Document] = relationship(back_populates="chunks")

    __table_args__ = (
        Index(
            "ix_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("ix_chunks_tsv", "tsv", postgresql_using="gin"),
    )


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)  # employees.id (không khoá ngoại: users đã bỏ)
    channel: Mapped[str] = mapped_column(String(16), default="web")  # web | teams | whatsapp | mcp
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Skill(Base):
    """Kỹ năng = quy trình/hướng dẫn tái sử dụng (định dạng giống Agent Skills: SKILL.md)."""

    __tablename__ = "skills"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    description: Mapped[str] = mapped_column(String(512))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="draft")  # draft | approved | deprecated
    version: Mapped[int] = mapped_column(Integer, default=1)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str] = mapped_column(String(64), default="system")
    embedding: Mapped[list[float]] = mapped_column(Vector(DIM))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Experience(Base):
    """Bài học agent rút ra sau mỗi nhiệm vụ -> được truy xuất cho nhiệm vụ tương tự sau này."""

    __tablename__ = "experiences"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_summary: Mapped[str] = mapped_column(Text)
    lesson: Mapped[str] = mapped_column(Text)
    outcome: Mapped[str] = mapped_column(String(16))  # success | failure
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    helpful_score: Mapped[int] = mapped_column(Integer, default=0)  # cập nhật theo feedback
    source_conversation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding: Mapped[list[float]] = mapped_column(Vector(DIM))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    conversation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event: Mapped[str] = mapped_column(String(32))  # llm_call | tool_call | tool_denied | refusal | ...
    detail: Mapped[dict] = mapped_column(JSONB, default=dict)


class UsageLog(Base):
    __tablename__ = "usage_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    department: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(64))
    purpose: Mapped[str] = mapped_column(String(32), default="chat")  # chat | reflection | miniapp
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_write_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0)


class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"))
    user_id: Mapped[int] = mapped_column(Integer)
    rating: Mapped[int] = mapped_column(Integer)  # 1 = 👍, -1 = 👎
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OcrJob(Base):
    """Job OCR bất đồng bộ (ADR-005). KHÔNG lưu file gốc và KHÔNG lưu tên file: chỉ metadata + kết quả.

    Dùng kiểu cột portable (JSON, không phải JSONB) để test được trên SQLite không cần Postgres.
    """

    __tablename__ = "ocr_jobs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # uuid4 hex, không đoán được
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(16), default="queued")  # queued | running | done | failed
    engine: Mapped[str] = mapped_column(String(32))
    kind: Mapped[str | None] = mapped_column(String(16), nullable=True)  # pdf | image, biết sau khi mở file
    bytes_in: Mapped[int] = mapped_column(Integer, default=0)
    pages_total: Mapped[int] = mapped_column(Integer, default=0)
    pages_done: Mapped[int] = mapped_column(Integer, default=0)
    result: Mapped[list | None] = mapped_column(JSON, nullable=True)  # [{page, text, source, ms}]
    error: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class SttJob(Base):
    """Job chép lời ghi âm (ADR-006). KHÔNG lưu file âm thanh và KHÔNG lưu tên file: chỉ metadata + kết quả.

    Cột kiểu portable (JSON, không phải JSONB) để test được trên SQLite. `user_id` là employees.id
    (như ocr_jobs).
    """

    __tablename__ = "stt_jobs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # uuid4 hex, không đoán được
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(16), default="queued")  # queued | running | done | failed
    engine: Mapped[str] = mapped_column(String(32))
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    bytes_in: Mapped[int] = mapped_column(Integer, default=0)
    duration_s: Mapped[float] = mapped_column(Float, default=0)  # tổng thời lượng, biết sau khi đổi định dạng
    done_s: Mapped[float] = mapped_column(Float, default=0)  # đã chép tới giây thứ mấy
    result: Mapped[list | None] = mapped_column(JSON, nullable=True)  # [{start, end, text}]
    error: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
