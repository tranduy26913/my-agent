"""POST /api/kb/ask (trang Tra cứu của portal).

Kiểm lớp API: xác thực bằng X-Portal-Token, tra người hỏi theo email trong bảng employees, schema camelCase.
Hàm `ask` (truy xuất + LLM) được thay bằng bản giả: logic đó đã có test riêng (test_rag_logic.py, eval), và
test này không được phụ thuộc model embedding hay LocalAI. Các ca cần nhân viên chạy trên Postgres thật trong
transaction rollback (tests/kb_testkit.py); không có DB thì skip.
"""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.api import ask as ask_module
from app.api.deps import get_db
from app.config import settings
from app.main import create_app
from app.rag.answer import AskResult
from app.rag.retriever import Hit
from tests.kb_testkit import _kb_db, add_employee  # noqa: F401  (_kb_db = fixture kb_db)

TOKEN = "tok-test-portal"


def make_hit() -> Hit:
    return Hit(
        chunk_id=1,
        doc_id="SVT-QC-003",
        so_hieu="01/2026/QĐ-SVT",
        title="Quy chế nghỉ phép",
        section="Điều 3",
        content="Mỗi năm 12 ngày phép",
        score=0.9,
        classification="thuong",
        effective_from=date(2026, 1, 1),
        effective_to=None,
        superseded_by=None,
        in_force=True,
    )


@pytest.fixture(name="client")
def _client(monkeypatch):
    monkeypatch.setattr(settings, "portal_bff_token", TOKEN)
    app = create_app()
    app.dependency_overrides[get_db] = lambda: None  # các ca 401/422 không chạm DB
    return TestClient(app)


@pytest.fixture(name="db_client")
def _db_client(kb_db, monkeypatch):
    monkeypatch.setattr(settings, "portal_bff_token", TOKEN)
    app = create_app()
    app.dependency_overrides[get_db] = lambda: kb_db
    return TestClient(app)


def headers(email="test.binh@saoviet.example", token=TOKEN):
    return {"X-Portal-Token": token, "X-User-Email": email}


# ---------- xác thực ----------


def test_khong_token_401(client):
    assert client.post("/api/kb/ask", json={"question": "x"}).status_code == 401


def test_sai_token_401(client):
    assert client.post("/api/kb/ask", json={"question": "x"}, headers=headers(token="sai")).status_code == 401


def test_chua_cau_hinh_token_thi_tu_choi_het(client, monkeypatch):
    monkeypatch.setattr(settings, "portal_bff_token", "")
    # token rỗng khớp với cấu hình rỗng cũng KHÔNG được qua (fail closed)
    assert client.post("/api/kb/ask", json={"question": "x"}, headers=headers(token="")).status_code == 401


def test_token_co_ky_tu_la_van_la_401_khong_phai_500(client):
    h = {
        "X-Portal-Token": "tôi-là-token".encode(),
        "X-User-Email": "a@b.c",
    }  # bytes: httpx không nhận str ngoài ASCII
    assert client.post("/api/kb/ask", json={"question": "x"}, headers=h).status_code == 401


def test_thieu_email_401(client):
    h = {"X-Portal-Token": TOKEN}
    assert client.post("/api/kb/ask", json={"question": "x"}, headers=h).status_code == 401


def test_token_cua_admin_kb_khong_dung_duoc_cho_ask(client):
    """JWT Bearer của /api/kb (admin) không thay được X-Portal-Token."""
    r = client.post(
        "/api/kb/ask",
        json={"question": "x"},
        headers={"Authorization": "Bearer abc", "X-User-Email": "a@b.c"},
    )
    assert r.status_code == 401


# ---------- dữ liệu vào ----------


@pytest.mark.parametrize(
    "body", [{}, {"question": ""}, {"question": "x" * 1001}, {"question": "x", "asOf": "không phải ngày"}]
)
def test_du_lieu_sai_422(client, body):
    assert client.post("/api/kb/ask", json=body, headers=headers()).status_code == 422


# ---------- người hỏi ----------


def test_khong_co_trong_danh_ba_403(db_client):
    r = db_client.post(
        "/api/kb/ask", json={"question": "nghỉ phép"}, headers=headers("khong.co@saoviet.example")
    )
    assert r.status_code == 403
    assert "danh bạ" in r.json()["detail"]


def test_nhan_vien_nghi_viec_403(db_client, kb_db):
    add_employee(kb_db, "TEST901", "test.nghi@saoviet.example", status="nghi-viec")
    r = db_client.post(
        "/api/kb/ask", json={"question": "nghỉ phép"}, headers=headers("test.nghi@saoviet.example")
    )
    assert r.status_code == 403
    assert "không còn hoạt động" in r.json()["detail"]


# ---------- thành công ----------


def test_tra_loi_co_trich_dan_camel_case(db_client, kb_db, monkeypatch):
    add_employee(kb_db, "TEST902", "test.binh@saoviet.example", department="HCNS", roles=["hr"])
    seen = {}

    def fake_ask(db, question, principal, as_of=None, audit=True):
        seen.update(question=question, dept=principal.department, roles=principal.roles, as_of=as_of)
        return AskResult(
            "Được 12 ngày phép [1].",
            True,
            ["SVT-QC-003 – Điều 3"],
            ["SVT-CS-001 – Điều 2"],
            [make_hit()],
            "qwen3-4b",
            latency_ms=1234,
        )

    monkeypatch.setattr(ask_module, "ask", fake_ask)
    r = db_client.post(
        "/api/kb/ask", json={"question": "  Được mấy ngày phép?  ", "asOf": "2024-06-30"}, headers=headers()
    )
    assert r.status_code == 200
    assert r.json() == {
        "answer": "Được 12 ngày phép [1].",
        "found": True,
        "citations": [{"n": 1, "label": "SVT-QC-003 – Điều 3", "docId": "SVT-QC-003"}],
        "withheld": ["SVT-CS-001 – Điều 2"],
        "asOf": "2024-06-30",
        "model": "qwen3-4b",
        "latencyMs": 1234,
    }
    # Phòng ban và vai trò lấy từ bảng employees, câu hỏi được cắt khoảng trắng, ngày tham chiếu truyền đúng.
    assert seen == {
        "question": "Được mấy ngày phép?",
        "dept": "HCNS",
        "roles": frozenset({"hr"}),
        "as_of": date(2024, 6, 30),
    }


def test_khong_co_as_of_thi_dung_hom_nay(db_client, kb_db, monkeypatch):
    add_employee(kb_db, "TEST903", "test.binh@saoviet.example")
    monkeypatch.setattr(
        ask_module, "ask", lambda db, q, p, as_of=None, audit=True: AskResult("Không rõ.", False)
    )
    r = db_client.post("/api/kb/ask", json={"question": "abc"}, headers=headers())
    assert r.status_code == 200
    assert r.json()["asOf"] == date.today().isoformat()
    assert r.json()["found"] is False and r.json()["citations"] == []
