"""Bước 4: nạp lại, cách ly, xoá (hàng loạt). Postgres thật, rollback sau mỗi test (tests/kb_testkit.py)."""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.deps import UserInfo, get_db, get_legacy_user
from app.main import create_app
from app.models import Chunk, Document
from app.rag import kb_service
from tests.kb_testkit import _kb_db, _kb_env, add_doc, audit_since_start  # noqa: F401  (_kb_db, _kb_env = fixture)
from tests.test_kb_upload import FRONTMATTER_MD, MD, META, PDF, PLAIN_MD, make_pdf, post, saved_files

URL = "/api/kb/documents"


def audit(db, event):
    return audit_since_start(db, event)


def doc_of(db, doc_id):
    db.expire_all()
    return db.execute(select(Document).where(Document.doc_id == doc_id)).scalar_one_or_none()


def chunks_of(db, doc_id):
    d = doc_of(db, doc_id)
    stmt = select(Chunk.id, Chunk.content).where(Chunk.document_id == d.id).order_by(Chunk.ordinal)
    rows = db.execute(stmt).all()
    return [(r.id, r.content) for r in rows]


def reindex(c, *ids):
    return c.post(f"{URL}:reindex", json={"docIds": list(ids)})


def delete(c, *ids):
    return c.post(f"{URL}:delete", json={"docIds": list(ids)})


# ---------------------------------------------------------------- quyền và route tĩnh

CASES = [("post", f"{URL}:reindex", {"docIds": ["X"]}), ("post", f"{URL}:delete", {"docIds": ["X"]}),
         ("put", f"{URL}/X/quarantine", {"on": True})]


@pytest.mark.parametrize("method,path,body", CASES)
def test_ghi_can_dang_nhap_va_admin(method, path, body):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: None
    assert getattr(TestClient(app), method)(path, json=body).status_code == 401
    app.dependency_overrides[get_legacy_user] = lambda: UserInfo(2, "nv", "manager", "KD")
    assert getattr(TestClient(app), method)(path, json=body).status_code == 403


def test_route_tinh_khong_bi_nham_voi_doc_id(kb_env):
    c, *_ = kb_env
    # nếu `documents:delete` bị hiểu là {doc_id} thì POST ra 405; đúng thì vào handler và báo 207 (không có)
    r = delete(c, "TEST-KB-KHONG-CO")
    assert r.status_code == 207 and "Không tìm thấy" in r.json()["detail"]


@pytest.mark.parametrize("ids", [[], [f"TEST-{i}" for i in range(kb_service.MAX_BATCH + 1)]])
def test_lo_rong_hoac_qua_lon_422(kb_env, ids):
    c, *_ = kb_env
    assert c.post(f"{URL}:reindex", json={"docIds": ids}).status_code == 422
    assert c.post(f"{URL}:delete", json={"docIds": ids}).status_code == 422


# ---------------------------------------------------------------- nạp lại

def test_reindex_thay_chunk_theo_noi_dung_moi_va_ghi_audit(kb_env, tmp_path):
    c, db, admin, _ = kb_env
    src = tmp_path / "knowledge" / "TEST-RI-1.md"
    src.parent.mkdir()
    src.write_text("# Quy chế\n\n## Điều 1\nNội dung bản đầu tiên của quy chế.\n", encoding="utf-8")
    add_doc(db, "TEST-RI-1", n_chunks=5, source=src.as_posix(), so_hieu="01/2026/TEST")
    assert len(chunks_of(db, "TEST-RI-1")) == 5

    new_text = "# Quy chế\n\n## Điều 1\nBản đã sửa lần hai.\n\n## Điều 2\nThêm một điều mới.\n"
    src.write_text(new_text, encoding="utf-8")
    r = reindex(c, "TEST-RI-1")
    assert r.status_code == 204 and r.content == b""
    new = chunks_of(db, "TEST-RI-1")
    assert len(new) == 2 and "Bản đã sửa lần hai" in new[0][1] and "Thêm một điều mới" in new[1][1]
    assert "TEST-RI-1" in new[0][1] and "01/2026/TEST" in new[0][1]  # tiền tố ngữ cảnh giống kb_ingest

    logs = audit(db, "kb_reindex")
    assert len(logs) == 1 and logs[0].detail == {"doc_id": "TEST-RI-1", "chunks": 2}
    assert logs[0].user_id == admin.id
    assert [h["text"] for h in c.get(f"{URL}/TEST-RI-1").json()["history"]] == ["Nạp lại tài liệu"]


def test_reindex_giu_nguyen_metadata_ban_cu_van_bi_thay_the(kb_env):
    """Lỗi cần tránh: ingest_markdown(force) ghi đè cột từ frontmatter, làm bản cũ 'sống lại'."""
    c, db, _, _ = kb_env
    assert post(c, "a.md", FRONTMATTER_MD.format(extra="").encode(), MD).status_code == 201
    meta = {**META, "supersedes": "TEST-UP-001", "effectiveFrom": "2026-05-01"}
    new_id = post(c, "b.md", PLAIN_MD.encode(), MD, meta).json()["docId"]

    assert reindex(c, "TEST-UP-001").status_code == 204
    old = doc_of(db, "TEST-UP-001")
    assert old.superseded_by == new_id and str(old.effective_to) == "2026-05-01"
    assert old.uploaded_by is not None and old.quarantined is False


def test_reindex_giu_trang_thai_cach_ly(kb_env):
    c, db, _, _ = kb_env
    post(c, "a.md", PLAIN_MD.encode(), MD, META)
    doc_id = db.execute(select(Document.doc_id).where(Document.doc_id.like("UPLOAD-%"))).scalars().first()
    assert c.put(f"{URL}/{doc_id}/quarantine", json={"on": True}).status_code == 204
    assert reindex(c, doc_id).status_code == 204
    assert doc_of(db, doc_id).quarantined is True


def test_reindex_pdf_cap_nhat_trang(kb_env):
    c, db, _, _ = kb_env
    assert post(c, "SVT-TB-050-x.pdf", make_pdf(2), PDF, META).status_code == 201
    before = chunks_of(db, "SVT-TB-050")
    assert reindex(c, "SVT-TB-050").status_code == 204
    after = chunks_of(db, "SVT-TB-050")
    assert [t for _, t in after] == [t for _, t in before]  # cùng nội dung
    assert {i for i, _ in after}.isdisjoint(i for i, _ in before)  # nhưng là các dòng chunk mới


def test_reindex_lo_co_mot_loi_cac_tai_lieu_khac_van_xong(kb_env, tmp_path):
    c, db, _, _ = kb_env
    good = tmp_path / "ok.md"
    good.write_text("# T\n\n## Điều 1\nNội dung hợp lệ.\n", encoding="utf-8")
    add_doc(db, "TEST-RI-GOOD1", n_chunks=4, source=good.as_posix())
    add_doc(db, "TEST-RI-GOOD2", n_chunks=4, source=good.as_posix())
    add_doc(db, "TEST-RI-BAD", n_chunks=3, source=(tmp_path / "mat-tich.md").as_posix())  # tệp gốc không còn

    r = reindex(c, "TEST-RI-GOOD1", "TEST-RI-BAD", "TEST-RI-GOOD2", "TEST-RI-GOOD1", "TEST-RI-KHONG-CO")
    assert r.status_code == 207
    body = r.json()
    assert "2/4" in body["detail"]
    assert "TEST-RI-BAD" in body["detail"] and "TEST-RI-KHONG-CO" in body["detail"]
    assert [(x["docId"], x["ok"]) for x in body["results"]] == [
        ("TEST-RI-GOOD1", True), ("TEST-RI-BAD", False), ("TEST-RI-GOOD2", True), ("TEST-RI-KHONG-CO", False),
    ]  # id trùng chỉ chạy một lần
    assert len(chunks_of(db, "TEST-RI-GOOD1")) == 1 and len(chunks_of(db, "TEST-RI-GOOD2")) == 1
    assert len(chunks_of(db, "TEST-RI-BAD")) == 3  # tài liệu lỗi giữ nguyên chunk cũ
    assert len(audit(db, "kb_reindex")) == 2  # chỉ ghi cho tài liệu thành công


def test_reindex_embed_hong_giu_chunk_cu(kb_env, tmp_path, monkeypatch):
    c, db, _, _ = kb_env
    src = tmp_path / "a.md"
    src.write_text("# T\n\n## Điều 1\nNội dung.\n", encoding="utf-8")
    add_doc(db, "TEST-RI-E", n_chunks=3, source=src.as_posix())
    old = chunks_of(db, "TEST-RI-E")

    class Boom:
        def embed(self, *_a, **_k):
            raise RuntimeError("model hỏng")

    monkeypatch.setattr(kb_service, "get_embedder", lambda: Boom())
    r = reindex(c, "TEST-RI-E")
    assert r.status_code == 207 and "Lỗi không xác định" in r.json()["detail"]
    assert "model hỏng" not in r.text  # không lộ chi tiết nội bộ ra response
    assert chunks_of(db, "TEST-RI-E") == old and audit(db, "kb_reindex") == []


def test_reindex_tep_khong_ho_tro(kb_env, tmp_path):
    c, db, _, _ = kb_env
    f = tmp_path / "ghi-chu.txt"
    f.write_text("nội dung", encoding="utf-8")
    add_doc(db, "TEST-RI-TXT", source=f.as_posix())
    r = reindex(c, "TEST-RI-TXT")
    assert r.status_code == 207 and ".txt" in r.json()["detail"]


# ---------------------------------------------------------------- cách ly

def test_quarantine_bat_tat_ghi_audit_va_lich_su(kb_env):
    c, db, admin, _ = kb_env
    add_doc(db, "TEST-QU-1")
    assert c.put(f"{URL}/TEST-QU-1/quarantine", json={"on": True}).status_code == 204
    listed = {d["docId"]: d for d in c.get(URL).json()}
    assert listed["TEST-QU-1"]["status"] == "quarantined"
    assert c.get(f"{URL}/TEST-QU-1/access", params={"email": "a@b.vn"}).status_code == 200

    assert c.put(f"{URL}/TEST-QU-1/quarantine", json={"on": True}).status_code == 204  # đã bật: không đổi gì
    assert len(audit(db, "kb_quarantine")) == 1

    assert c.put(f"{URL}/TEST-QU-1/quarantine", json={"on": False}).status_code == 204
    assert {d["docId"]: d for d in c.get(URL).json()}["TEST-QU-1"]["status"] == "ready"
    logs = audit(db, "kb_quarantine")
    assert [x.detail["on"] for x in logs] == [True, False] and logs[0].user_id == admin.id
    hist = [h["text"] for h in c.get(f"{URL}/TEST-QU-1").json()["history"]]
    assert hist == ["Bỏ cách ly tài liệu", "Cách ly tài liệu"]


def test_quarantine_404_va_body_sai(kb_env):
    c, *_ = kb_env
    assert c.put(f"{URL}/TEST-KHONG-CO/quarantine", json={"on": True}).status_code == 404
    assert c.put(f"{URL}/TEST-KHONG-CO/quarantine", json={"bat": True}).status_code == 422


def test_tai_lieu_cach_ly_bi_retriever_loai(kb_env):
    """Cờ đặt ở đây phải thật sự chặn truy xuất: dùng đúng điều kiện SQL mà retriever.retrieve áp dụng."""
    c, db, _, _ = kb_env
    add_doc(db, "TEST-QU-2")
    base = select(Document.doc_id).where(Document.doc_id == "TEST-QU-2", Document.quarantined.is_(False))
    assert db.execute(base).first() is not None
    c.put(f"{URL}/TEST-QU-2/quarantine", json={"on": True})
    db.expire_all()
    assert db.execute(base).first() is None


# ---------------------------------------------------------------- xoá

def test_delete_xoa_tai_lieu_chunk_tep_va_ghi_audit(kb_env):
    c, db, admin, folder = kb_env
    assert post(c, "SVT-TB-060-x.pdf", make_pdf(2), PDF, {**META, "classified": True}).status_code == 201
    pid = doc_of(db, "SVT-TB-060").id
    assert len(saved_files(folder)) == 1

    r = delete(c, "SVT-TB-060")
    assert r.status_code == 204
    assert doc_of(db, "SVT-TB-060") is None
    left = select(func.count()).select_from(Chunk).where(Chunk.document_id == pid)
    assert db.execute(left).scalar_one() == 0
    assert saved_files(folder) == []
    logs = [x for x in audit(db, "kb_delete") if x.detail["doc_id"] == "SVT-TB-060"]
    assert len(logs) == 1 and logs[0].user_id == admin.id
    assert logs[0].detail["classified"] is True and logs[0].detail["chunks"] >= 2
    assert c.get(f"{URL}/SVT-TB-060").status_code == 404


def test_delete_tep_dung_chung_chi_xoa_khi_het_nguoi_dung(kb_env):
    c, db, _, folder = kb_env
    pdf = make_pdf(1)  # cùng nội dung -> cùng <sha>.pdf
    assert post(c, "SVT-TB-061-a.pdf", pdf, PDF, META).status_code == 201
    assert post(c, "SVT-TB-062-b.pdf", pdf, PDF, META).status_code == 201
    assert len(saved_files(folder)) == 1
    assert delete(c, "SVT-TB-061").status_code == 204
    assert len(saved_files(folder)) == 1  # tài liệu kia vẫn cần bản gốc
    assert delete(c, "SVT-TB-062").status_code == 204
    assert saved_files(folder) == []


def test_delete_khong_dung_toi_tep_ngoai_upload_dir(kb_env, tmp_path):
    c, db, _, _ = kb_env
    kb_file = tmp_path / "knowledge" / "SVT-QC-999.md"
    kb_file.parent.mkdir()
    kb_file.write_text("# nguồn gốc của kho tri thức", encoding="utf-8")
    add_doc(db, "TEST-DEL-KB", source=kb_file.as_posix())
    assert delete(c, "TEST-DEL-KB").status_code == 204
    assert doc_of(db, "TEST-DEL-KB") is None
    assert kb_file.exists()  # chỉ gỡ khỏi DB, tệp trong data/knowledge còn nguyên


def test_delete_go_lien_ket_thay_the(kb_env):
    c, db, _, _ = kb_env
    add_doc(db, "TEST-DEL-OLD")
    meta = {**META, "supersedes": "TEST-DEL-OLD", "effectiveFrom": "2026-05-01"}
    new_id = post(c, "a.md", PLAIN_MD.encode(), MD, meta).json()["docId"]
    assert doc_of(db, "TEST-DEL-OLD").superseded_by == new_id

    assert delete(c, new_id).status_code == 204  # xoá bản mới -> bản cũ không còn trỏ vào hư không
    assert doc_of(db, "TEST-DEL-OLD").superseded_by is None

    add_doc(db, "TEST-DEL-OLD2")
    meta2 = {**META, "supersedes": "TEST-DEL-OLD2"}
    new2 = post(c, "b.md", PLAIN_MD.replace("họp", "họp lại").encode(), MD, meta2)
    new2_id = new2.json()["docId"]
    assert delete(c, "TEST-DEL-OLD2").status_code == 204  # xoá bản cũ -> bản mới không còn "thay thế" ai
    assert doc_of(db, new2_id).supersedes is None


def test_delete_lo_co_tai_lieu_khong_ton_tai(kb_env):
    c, db, _, _ = kb_env
    add_doc(db, "TEST-DEL-A")
    add_doc(db, "TEST-DEL-B")
    r = delete(c, "TEST-DEL-A", "TEST-DEL-KHONG-CO", "TEST-DEL-B")
    assert r.status_code == 207 and "1/3" in r.json()["detail"]
    assert doc_of(db, "TEST-DEL-A") is None and doc_of(db, "TEST-DEL-B") is None
    assert len([x for x in audit(db, "kb_delete") if x.detail["doc_id"].startswith("TEST-DEL-")]) == 2


def test_delete_loi_giua_chung_rollback_tai_lieu_do(kb_env, monkeypatch):
    c, db, _, folder = kb_env
    assert post(c, "SVT-TB-063-x.pdf", make_pdf(1), PDF, META).status_code == 201

    def boom(*_a, **_k):
        raise RuntimeError("commit hỏng")

    monkeypatch.setattr(db, "commit", boom)  # DELETE đã chạy trong transaction nhưng commit thất bại
    r = delete(c, "SVT-TB-063")
    assert r.status_code == 207
    assert doc_of(db, "SVT-TB-063") is not None and len(chunks_of(db, "SVT-TB-063")) >= 1  # chunk không mất
    assert len(saved_files(folder)) == 1 and audit(db, "kb_delete") == []


def test_body_json_dang_camel_case(kb_env):
    c, db, _, _ = kb_env
    add_doc(db, "TEST-DEL-C")
    r = c.post(f"{URL}:delete", content=json.dumps({"docIds": ["TEST-DEL-C"]}),
               headers={"Content-Type": "application/json"})
    assert r.status_code == 204
