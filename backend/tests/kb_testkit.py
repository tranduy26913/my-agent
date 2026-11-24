"""Đồ nghề test /api/kb cần Postgres thật (agent-db): fixture `kb_db` và các hàm dựng dữ liệu mẫu.

`kb_db` mở một transaction NGOÀI rồi rollback khi test xong, nên không để lại dòng nào trong DB thật,
kể cả khi code được test gọi `db.commit()` (join_transaction_mode="create_savepoint": commit chỉ chốt
savepoint bên trong). Không kết nối được DB thì test được bỏ qua (skip), giống tests/test_hr_authz.py.

.NET: tương đương bọc mỗi test trong `TransactionScope` rồi không gọi Complete().
Mọi mã/ID dữ liệu mẫu có tiền tố TEST để không đụng dữ liệu thật.
"""

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import DIM, AuditLog, Chunk, Document, Employee, User


@pytest.fixture(name="kb_db")
def _kb_db():  # test import hàm này (noqa F401) để pytest thấy fixture; xem cách dùng ở test_kb_service.py
    url = settings.database_url.replace("@localhost:", "@127.0.0.1:")  # tránh treo khi localhost -> ::1
    engine = create_engine(url, connect_args={"connect_timeout": 3})
    try:
        conn = engine.connect()
    except Exception as e:  # noqa: BLE001
        engine.dispose()
        pytest.skip(f"Không kết nối được DB: {e}")
    outer = conn.begin()
    session = Session(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
    # DB thật có thể đã có dòng audit từ lần dùng thật; test chỉ đếm dòng do chính nó tạo (id > mốc này).
    max_id = select(func.coalesce(func.max(AuditLog.id), 0))
    session.info["audit_floor"] = session.execute(max_id).scalar_one()
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        conn.close()
        engine.dispose()


def audit_since_start(db, event):
    """Dòng audit loại `event` do test hiện tại tạo ra, không tính dữ liệu có sẵn trong DB thật."""
    stmt = select(AuditLog).where(AuditLog.event == event, AuditLog.id > db.info.get("audit_floor", 0))
    return db.execute(stmt.order_by(AuditLog.id)).scalars().all()


def add_user(db, username="test.admin", role="admin") -> User:
    u = User(username=username, full_name="Quản trị thử", password_hash="x", role=role, department="CNTT")
    db.add(u)
    db.commit()  # commit (chỉ chốt savepoint): để rollback trong code được test không xoá dữ liệu mẫu
    return u


def add_employee(db, code, email, department="KD", roles=(), status="dang-lam", name="Người Thử") -> Employee:
    e = Employee(code=code, full_name=name, department=department, title="Nhân viên", email=email,
                 roles=list(roles), status=status)
    db.add(e)
    db.commit()
    return e


def add_doc(db, doc_id, n_chunks=2, **fields) -> Document:
    fields.setdefault("title", f"Tài liệu {doc_id}")
    fields.setdefault("source", f"data/knowledge/{doc_id}.md")
    fields.setdefault("department", "HCNS")
    d = Document(doc_id=doc_id, **fields)
    d.chunks = [
        Chunk(ordinal=i, page=None, section=f"Điều {i + 1}", content=f"Nội dung đoạn {i} của {doc_id}",
              embedding=[0.0] * DIM)
        for i in range(n_chunks)
    ]
    db.add(d)
    db.commit()
    return d


@pytest.fixture(name="kb_env")
def _kb_env(kb_db, tmp_path, monkeypatch):
    """Client admin + DB rollback + upload_dir tạm + embedder băm (không tải model e5).

    Trả (client, db, admin, thư mục upload).
    """
    from fastapi.testclient import TestClient

    from app.api.deps import UserInfo, get_db, get_legacy_user
    from app.main import create_app
    from app.rag.embeddings import get_embedder

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "embedding_provider", "hash")
    get_embedder.cache_clear()
    admin = add_user(kb_db)
    app = create_app()
    app.dependency_overrides[get_db] = lambda: kb_db
    app.dependency_overrides[get_legacy_user] = lambda: UserInfo(admin.id, "test.admin", "admin", "CNTT")
    yield TestClient(app, raise_server_exceptions=False), kb_db, admin, tmp_path / "uploads"
    get_embedder.cache_clear()
