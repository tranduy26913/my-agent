"""GET /api/admin/audit và /api/admin/usage. Dữ liệu mẫu nằm trong transaction rollback (tests/kb_testkit.py),
mốc thời gian năm 2099 để không lẫn với dòng thật có sẵn trong agent-db."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api.deps import UserInfo, get_db, get_legacy_user
from app.main import create_app
from app.models import AuditLog, UsageLog
from tests.kb_testkit import _kb_db, add_employee, add_user  # noqa: F401  (_kb_db = fixture kb_db)

DAY = {"since": "2099-01-01", "until": "2099-01-31"}


def ts(day: int, hour: int = 9) -> datetime:
    return datetime(2099, 1, day, hour, tzinfo=UTC)


@pytest.fixture(name="api")
def _api(kb_db):
    admin = add_user(kb_db, "test.admin")
    app = create_app()
    app.dependency_overrides[get_db] = lambda: kb_db
    app.dependency_overrides[get_legacy_user] = lambda: UserInfo(admin.id, "test.admin", "admin", "CNTT")
    return TestClient(app), kb_db, admin


# ---------------------------------------------------------------- quyền


@pytest.mark.parametrize("path", ["/api/admin/audit", "/api/admin/usage"])
def test_can_dang_nhap_va_admin(path):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: None
    assert TestClient(app).get(path).status_code == 401
    app.dependency_overrides[get_legacy_user] = lambda: UserInfo(2, "nv", "staff", "KD")
    assert TestClient(app).get(path).status_code == 403


# ---------------------------------------------------------------- audit


def test_audit_lam_noi_su_kien_nhay_cam_va_giai_ma_nguoi_thuc_hien(api):
    c, db, admin = api
    emp = add_employee(db, "TEST-AU1", "test.hoi@test.example", name="Người Hỏi")
    db.add_all(
        [
            # id bảng users: tên lấy từ users
            AuditLog(
                ts=ts(1),
                user_id=admin.id,
                event="kb_upload",
                detail={"doc_id": "D1", "kind": "md", "chunks": 3},
            ),
            # người dùng Zitadel: email trong detail.actor, user_id NULL
            AuditLog(
                ts=ts(2),
                user_id=None,
                event="kb_view_classified",
                detail={"doc_id": "D2", "actor": "zit@test.example"},
            ),
            # RAG ghi employees.id: KHÔNG được join sang users dù id trùng một dòng users
            AuditLog(
                ts=ts(3),
                user_id=admin.id,
                event="rag_ask",
                detail={"email": emp.email, "question": "BÍ-MẬT-Q", "found": True},
            ),
            AuditLog(
                ts=ts(4),
                user_id=admin.id,
                event="tool_denied",
                detail={"tool": "hr_lookup", "input": {"x": "BÍ-MẬT-T"}, "output_preview": "BÍ-MẬT-O"},
            ),
        ]
    )
    db.commit()
    r = c.get("/api/admin/audit", params=DAY)
    assert r.status_code == 200
    by_event = {i["event"]: i for i in r.json()["items"]}
    assert by_event["kb_upload"]["actor"] == "test.admin" and by_event["kb_upload"]["highlight"] is None
    assert by_event["kb_view_classified"]["actor"] == "zit@test.example"
    assert by_event["kb_view_classified"]["highlight"] == "alert"
    assert (
        by_event["tool_denied"]["highlight"] == "alert" and by_event["tool_denied"]["summary"] == "hr_lookup"
    )
    assert by_event["rag_ask"]["actor"] == "test.hoi@test.example"  # không phải "test.admin"
    assert by_event["rag_ask"]["summary"] == "Có câu trả lời"
    # quyền riêng tư: không rò nội dung câu hỏi, tham số, kết quả của tool; email không nằm trong detail
    body = r.text
    assert "BÍ-MẬT" not in body and "test.hoi@test.example" in by_event["rag_ask"]["actor"]
    assert "email" not in by_event["rag_ask"]["detail"] and "question" not in by_event["rag_ask"]["detail"]
    assert by_event["tool_denied"]["detail"] == {"tool": "hr_lookup"}


def test_audit_su_kien_la_khong_tra_detail(api):
    c, db, _ = api
    db.add(AuditLog(ts=ts(5), event="su_kien_moi", detail={"noi_dung": "NHAY-CAM"}))
    db.commit()
    item = next(
        i for i in c.get("/api/admin/audit", params=DAY).json()["items"] if i["event"] == "su_kien_moi"
    )
    assert item["detail"] == {} and item["label"] == "su_kien_moi" and item["actor"] == "hệ thống"


def test_audit_loc_theo_su_kien_nguoi_va_ngay(api):
    c, db, admin = api
    db.add_all(
        [
            AuditLog(ts=ts(10), user_id=admin.id, event="kb_upload", detail={"doc_id": "A"}),
            AuditLog(ts=ts(11), event="kb_delete", detail={"doc_id": "B", "actor": "lan_dan@test.example"}),
            AuditLog(ts=ts(20), event="kb_delete", detail={"doc_id": "C", "actor": "khac@test.example"}),
        ]
    )
    db.commit()

    def docs(**params):
        items = c.get("/api/admin/audit", params={**DAY, **params}).json()["items"]
        return sorted(i["summary"] for i in items)

    assert docs(event="kb_delete") == ["B", "C"]
    assert docs(event=["kb_delete", "kb_upload"]) == ["A", "B", "C"]
    assert docs(actor="LAN_DAN") == ["B"]  # không phân biệt hoa thường
    assert docs(actor="lan%dan") == []  # % và _ không phải ký tự đại diện của người dùng nhập
    assert docs(since="2099-01-11", until="2099-01-11") == ["B"]  # gồm cả ngày kết thúc
    assert c.get("/api/admin/audit", params={"since": "2099-02-01", "until": "2099-01-01"}).status_code == 422


def test_audit_phan_trang_bang_con_tro(api):
    c, db, _ = api
    db.add_all([AuditLog(ts=ts(15, h), event="kb_reindex", detail={"doc_id": f"P{h}"}) for h in range(1, 6)])
    db.commit()
    p1 = c.get("/api/admin/audit", params={**DAY, "limit": 2}).json()
    assert [i["summary"] for i in p1["items"]] == ["P5", "P4"] and p1["nextCursor"] is not None
    p2 = c.get("/api/admin/audit", params={**DAY, "limit": 2, "beforeId": p1["nextCursor"]}).json()
    assert [i["summary"] for i in p2["items"]] == ["P3", "P2"]
    p3 = c.get("/api/admin/audit", params={**DAY, "limit": 2, "beforeId": p2["nextCursor"]}).json()
    assert [i["summary"] for i in p3["items"]] == ["P1"] and p3["nextCursor"] is None
    assert p1["eventLabels"]["kb_reindex"] == "Nạp lại tài liệu" and p1["eventCounts"]["kb_reindex"] >= 5


# ---------------------------------------------------------------- usage


def usage(db, user_id, purpose, model, day=3, cost=0.0, inp=0, out=0, dept="KD"):
    db.add(
        UsageLog(
            ts=ts(day),
            user_id=user_id,
            department=dept,
            model=model,
            purpose=purpose,
            input_tokens=inp,
            output_tokens=out,
            cost_usd=cost,
        )
    )


def test_usage_tong_hop_theo_thang_va_phan_giai_ten_dung_bang(api):
    c, db, admin = api
    emp = add_employee(db, "TEST-US1", "test.us@test.example", name="Nhân Viên Rag")
    usage(db, emp.id, "rag", "claude-sonnet-5-5", day=3, cost=0.5, inp=1000, out=200)
    usage(db, emp.id, "rag", "local:qwen3-4b", day=3, inp=500, out=100)
    usage(db, admin.id, "chat", "local:tesseract", day=4)
    usage(
        db, 2_000_000_000, "chat", "claude-opus-5-5", day=4, cost=1.25, inp=10, out=5
    )  # users.id không tồn tại
    # tháng khác không được lẫn vào
    db.add(
        UsageLog(
            ts=datetime(2098, 12, 31, tzinfo=UTC), user_id=admin.id, department="X", model="m", purpose="chat"
        )
    )
    db.commit()

    r = c.get("/api/admin/usage", params={"month": "2099-01"})
    assert r.status_code == 200
    d = r.json()
    assert (d["month"], d["calls"], d["inputTokens"], d["outputTokens"]) == ("2099-01", 4, 1510, 305)
    assert d["costUsd"] == pytest.approx(1.75) and "2099-01" in d["months"] and "2098-12" in d["months"]
    assert d["budgetUsdPerUser"] > 0
    names = {g["key"]: g["name"] for g in d["byUser"]}
    # purpose rag/ocr -> employees; chat -> users; id lạ -> nhãn dự phòng, không nhầm tên người khác
    assert names[f"e{emp.id}"] == "Nhân Viên Rag"
    assert names[f"u{admin.id}"] == "test.admin"
    assert names["u2000000000"] == "Người dùng #2000000000"
    rag = next(g for g in d["byUser"] if g["key"] == f"e{emp.id}")
    assert (rag["calls"], rag["inputTokens"], rag["costUsd"]) == (2, 1500, 0.5)
    assert {g["name"]: g["calls"] for g in d["byModel"]}["local:qwen3-4b"] == 1
    assert d["byModel"][0]["name"] == "claude-opus-5-5"  # xếp theo chi phí giảm dần
    assert {g["name"]: g["calls"] for g in d["byPurpose"]} == {"rag": 2, "chat": 2}
    assert [(g["name"], g["calls"]) for g in d["byDay"]] == [("2099-01-03", 2), ("2099-01-04", 2)]


def test_usage_thang_khong_co_du_lieu_va_tham_so_xau(api):
    c, _, _ = api
    d = c.get("/api/admin/usage", params={"month": "2097-05"}).json()
    assert d["calls"] == 0 and d["byUser"] == [] and d["byDay"] == [] and d["costUsd"] == 0
    for bad in ("2099-13", "2099-1", "abc", "2099-01-05"):
        assert c.get("/api/admin/usage", params={"month": bad}).status_code == 422
    assert c.get("/api/admin/usage").status_code == 200  # mặc định tháng hiện tại
