"""/api/hr/*: nghỉ phép và danh bạ theo ADR-003 (RBAC có phạm vi). Token Zitadel tự ký, DB thật qua transaction rollback.

Ba bảng mới (leave_balances, leave_requests, employee_contacts) được tạo TRONG transaction rollback của test (DDL của
Postgres rollback được): test chạy cả khi agent-db chưa có bảng, và không để lại gì ở đó.

Tổ chức mẫu (mã TEST-, phòng ban mang tên riêng để phạm vi `dept` không dính nhân viên thật trong agent-db):

    CEO (executive, TBGD)
     ├─ TP (manager+truong-phong, TDA) ── MG (manager, TDA) ── LEAD (manager, TDA) ── S1, S2 (TDA), GONE (nghỉ việc)
     └─ X (employee, TKD)
    HR (hr, THC)    ADM (employee+admin, TIT)

Nhân viên thật trong agent-db cũng có mặt (hr thấy "all"), nên mọi so sánh lọc theo mã bắt đầu bằng TEST-.
"""

import json
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.deps import get_db
from app.auth.oidc import get_verifier
from app.db import Base
from app.hr import service
from app.hr.authz import Target, can_view_employee, can_view_phone, directory_sql
from app.main import create_app
from app.models import Employee, EmployeeContact, LeaveBalance, LeaveRequest
from app.rag.acl import load_principal
from app.seed_hr import load_all, read
from tests.kb_testkit import _kb_db, add_employee, audit_since_start  # noqa: F401  (_kb_db = fixture kb_db)
from tests.oidc_testkit import Idp, bearer

YEAR = date.today().year


def email(code: str) -> str:
    return f"{code.lower()}@test.example"


ORG = [
    # code, phòng, vai trò, quản lý trực tiếp, trạng thái, họ tên, số điện thoại
    ("TEST-CEO", "TBGD", ["executive"], None, "dang-lam", "Phạm Test Tổng", "0900 000 001"),
    ("TEST-TP", "TDA", ["manager", "truong-phong"], "TEST-CEO", "dang-lam", "Nguyễn Thị Trưởng Phòng", "0900 000 002"),
    ("TEST-MG", "TDA", ["manager"], "TEST-TP", "dang-lam", "Trần Quản Lý", "0900 000 003"),
    ("TEST-LEAD", "TDA", ["manager"], "TEST-MG", "dang-lam", "Lê Trưởng Nhóm", "0900 000 004"),
    ("TEST-S1", "TDA", ["employee"], "TEST-LEAD", "dang-lam", "Đỗ Nhân Viên Một", "0900 000 005"),
    ("TEST-S2", "TDA", ["employee"], "TEST-LEAD", "dang-lam", "Hồ Nhân Viên Hai", "0900 000 006"),
    ("TEST-GONE", "TDA", ["employee"], "TEST-LEAD", "da-nghi-viec", "Vũ Đã Nghỉ", "0900 000 007"),
    ("TEST-X", "TKD", ["employee"], "TEST-CEO", "dang-lam", "Ngô Kinh Doanh", "0900 000 008"),
    ("TEST-HR", "THC", ["hr"], None, "dang-lam", "Đinh Nhân Sự", "0900 000 009"),
    ("TEST-ADM", "TIT", ["employee", "admin"], None, "dang-lam", "Kim Quản Trị", "0900 000 010"),
]
REQUESTS = [
    # mã đơn, nhân viên, trạng thái, ghi chú
    ("TEST-DP-1", "TEST-S1", "cho-duyet", "GHI-CHU-RIENG-S1"),
    ("TEST-DP-2", "TEST-S2", "da-duyet", "GHI-CHU-RIENG-S2"),
    ("TEST-DP-3", "TEST-LEAD", "cho-duyet", "GHI-CHU-RIENG-LEAD"),
    ("TEST-DP-4", "TEST-X", "da-duyet", "GHI-CHU-RIENG-X"),
    ("TEST-DP-5", "TEST-GONE", "da-duyet", "GHI-CHU-RIENG-GONE"),
    ("TEST-DP-6", "TEST-TP", "da-duyet", "GHI-CHU-RIENG-TP"),
]


@pytest.fixture(name="env")
def _env(kb_db):
    tables = [m.__table__ for m in (LeaveBalance, LeaveRequest, EmployeeContact)]
    Base.metadata.create_all(bind=kb_db.connection(), tables=tables)
    kb_db.commit()

    for code, dept, roles, mgr, status, name, phone in ORG:
        e = add_employee(kb_db, code, email(code), department=dept, roles=roles, status=status, name=name)
        e.manager_code = mgr
        kb_db.add(EmployeeContact(employee_code=code, phone=phone))
        kb_db.add(LeaveBalance(employee_code=code, year=YEAR, entitled=12, carried_over=1, used=3, remaining=10))
    for code, who, status, note in REQUESTS:
        kb_db.add(
            LeaveRequest(
                code=code, employee_code=who, kind="phep-nam", from_date=date(YEAR, 3, 2), to_date=date(YEAR, 3, 3),
                days=2, status=status, approver_code="TEST-LEAD", note=note,
            )
        )
    kb_db.commit()

    idp = Idp()
    app = create_app()
    app.dependency_overrides[get_db] = lambda: kb_db
    app.dependency_overrides[get_verifier] = idp.verifier
    client = TestClient(app, raise_server_exceptions=False)

    def get(who: str | None, path: str, **params):
        headers = bearer(idp.token(email=email(who), sub=f"s-{who}")) if who else {}
        return client.get(path, headers=headers, params=params)

    return get, kb_db


def codes(rows, key=lambda r: r["person"]["code"]) -> list[str]:
    return sorted(c for c in (key(r) for r in rows) if c.startswith("TEST-"))


# ---------------------------------------------------------------- đăng nhập


def test_can_dang_nhap_va_la_nhan_vien_dang_lam(env):
    get, _ = env
    for path in ("/api/hr/leave/me", "/api/hr/leave/team", "/api/hr/directory"):
        assert get(None, path).status_code == 401
    assert get("TEST-GONE", "/api/hr/leave/me").status_code == 403  # đã nghỉ việc: từ chối tất cả (ADR-003 mục 3)


# ---------------------------------------------------------------- nghỉ phép của chính mình


def test_chi_thay_phep_cua_chinh_minh_va_danh_tinh_khong_lay_tu_tham_so(env):
    get, _ = env
    r = get("TEST-S1", "/api/hr/leave/me", code="TEST-S2", employeeCode="TEST-S2", email=email("TEST-HR"))
    d = r.json()
    assert r.status_code == 200 and d["person"]["code"] == "TEST-S1"  # T14: tham số "tôi là người khác" vô hiệu
    assert d["balance"]["remaining"] == 10 and d["balance"]["entitled"] == 12
    assert [x["code"] for x in d["requests"]] == ["TEST-DP-1"]
    assert d["requests"][0]["note"] == "GHI-CHU-RIENG-S1" and d["requests"][0]["approverName"] == "Lê Trưởng Nhóm"
    assert d["canViewTeam"] is False
    assert "GHI-CHU-RIENG-S2" not in r.text


def test_nam_khong_co_du_lieu_thi_balance_null(env):
    get, _ = env
    d = get("TEST-S1", "/api/hr/leave/me", year=2000).json()
    assert d["year"] == 2000 and d["balance"] is None and d["requests"] != []  # đơn không phân theo năm
    assert get("TEST-S1", "/api/hr/leave/me", year=1999).status_code == 422


def test_can_view_team_theo_vai_tro(env):
    get, _ = env
    flags = {c: get(c, "/api/hr/leave/me").json()["canViewTeam"] for c in ("TEST-S1", "TEST-LEAD", "TEST-TP", "TEST-CEO", "TEST-HR", "TEST-ADM")}
    assert flags == {
        "TEST-S1": False, "TEST-LEAD": True, "TEST-TP": True, "TEST-CEO": True, "TEST-HR": True, "TEST-ADM": False,
    }


# ---------------------------------------------------------------- phép của người khác (ADR-003 T2–T11)


def test_nhan_vien_va_admin_bi_tu_choi_va_bi_ghi_lai(env):
    get, db = env
    for code in ("TEST-S1", "TEST-ADM"):  # T2, T11: admin không có quyền dữ liệu HR
        r = get(code, "/api/hr/leave/team")
        assert r.status_code == 403 and "người khác" in r.json()["detail"], code
    denied = audit_since_start(db, "hr_denied")
    assert [d.detail for d in denied] == [
        {"resource": "leave_team", "reason": "no_scope", "actor": email("TEST-S1")},
        {"resource": "leave_team", "reason": "no_scope", "actor": email("TEST-ADM")},
    ]


def test_truong_nhom_chi_thay_cap_duoi_truc_tiep_va_khong_thay_nguoi_nghi(env):  # T4, T7
    get, _ = env
    d = get("TEST-LEAD", "/api/hr/leave/team").json()
    assert d["scopes"] == ["team"]
    assert codes(d["members"]) == ["TEST-S1", "TEST-S2"]  # GONE đã nghỉ: không có inactive
    assert codes(d["requests"], key=lambda r: r["employee"]["code"]) == ["TEST-S1", "TEST-S2"]
    by = {m["person"]["code"]: m for m in d["members"]}
    assert by["TEST-S1"]["pending"] == 1 and by["TEST-S2"]["pending"] == 0
    assert by["TEST-S1"]["balance"]["remaining"] == 10


def test_quan_ly_cach_hai_cap_khong_thay_nhan_vien(env):  # T5: team không đệ quy
    get, _ = env
    d = get("TEST-MG", "/api/hr/leave/team").json()
    assert codes(d["members"]) == ["TEST-LEAD"]
    assert "GHI-CHU-RIENG-S1" not in json.dumps(d)


def test_truong_phong_thay_ca_phong_nhung_khong_thay_phong_khac(env):  # T6
    get, _ = env
    d = get("TEST-TP", "/api/hr/leave/team").json()
    assert d["scopes"] == ["team", "dept"]
    assert codes(d["members"]) == ["TEST-LEAD", "TEST-MG", "TEST-S1", "TEST-S2"]  # không có chính mình, GONE, X
    assert sorted(r["code"] for r in d["requests"] if r["code"].startswith("TEST-")) == [
        "TEST-DP-1", "TEST-DP-2", "TEST-DP-3",
    ]


def test_giam_doc_chi_thay_cap_duoi_truc_tiep(env):  # T9, T10
    get, _ = env
    d = get("TEST-CEO", "/api/hr/leave/team").json()
    assert d["scopes"] == ["team"]
    assert codes(d["members"]) == ["TEST-TP", "TEST-X"]


def test_hr_thay_tat_ca_ke_ca_nguoi_da_nghi(env):  # T3
    get, _ = env
    d = get("TEST-HR", "/api/hr/leave/team").json()
    assert d["scopes"] == ["all"]
    assert "TEST-GONE" in codes(d["members"])  # HR có directory:read:inactive
    assert set(c for c in codes(d["members"]) if c != "TEST-GONE") >= {
        "TEST-CEO", "TEST-TP", "TEST-MG", "TEST-LEAD", "TEST-S1", "TEST-S2", "TEST-X", "TEST-ADM",
    }
    assert "TEST-HR" not in codes(d["members"])  # phép của chính mình nằm ở /leave/me


def test_xem_nguoi_khac_duoc_ghi_audit_khong_chua_du_lieu(env):
    get, db = env
    get("TEST-LEAD", "/api/hr/leave/team")
    get("TEST-S1", "/api/hr/leave/me")  # xem của chính mình: không ghi
    (row,) = audit_since_start(db, "hr_view")
    assert row.user_id is None
    assert row.detail == {"resource": "leave_team", "scopes": ["team"], "rows": 4, "actor": email("TEST-LEAD")}
    text = json.dumps(row.detail)
    assert "GHI-CHU" not in text and "Nhân Viên" not in text


def test_chot_chan_thu_hai_bo_dong_ma_can_tu_choi(env, monkeypatch):
    """ADR-003 mục 9: nếu bản SQL lỡ trả dòng mà bản Python từ chối thì dòng đó không được ra khỏi service."""
    get, _ = env
    real_can = service.can
    monkeypatch.setattr(
        service, "can", lambda p, res, t: real_can(p, res, t) if t.code != "TEST-S1" else real_can(p, "salary:read", t)
    )
    d = get("TEST-LEAD", "/api/hr/leave/team").json()
    assert codes(d["members"]) == ["TEST-S2"]
    assert codes(d["requests"], key=lambda r: r["employee"]["code"]) == ["TEST-S2"]


# ---------------------------------------------------------------- danh bạ (T8, T12, T13)


def test_danh_ba_che_so_dien_thoai_theo_phong_ban(env):
    get, _ = env
    d = get("TEST-S1", "/api/hr/directory", q="TEST-").json()
    rows = {r["person"]["code"]: r for r in d["items"]}
    assert "TEST-GONE" not in rows  # người đã nghỉ bị ẩn
    assert rows["TEST-S2"]["phone"] == "0900 000 006" and rows["TEST-S2"]["phoneVisible"] is True  # cùng phòng
    x = rows["TEST-X"]  # khác phòng: tên vẫn hiện, số bị che
    assert x["person"]["name"] == "Ngô Kinh Doanh" and x["phone"] is None and x["phoneVisible"] is False
    assert "0900 000 008" not in json.dumps(d)
    assert rows["TEST-S1"]["phone"] == "0900 000 005"  # số của chính mình


def test_danh_ba_hr_va_giam_doc_thay_het_so(env):
    get, _ = env
    hr = {r["person"]["code"]: r for r in get("TEST-HR", "/api/hr/directory", q="TEST-").json()["items"]}
    assert hr["TEST-GONE"]["active"] is False and hr["TEST-GONE"]["phone"] == "0900 000 007"  # T8
    assert hr["TEST-X"]["phone"] == "0900 000 008"
    ceo = {r["person"]["code"]: r for r in get("TEST-CEO", "/api/hr/directory", q="TEST-").json()["items"]}
    assert ceo["TEST-X"]["phone"] == "0900 000 008" and "TEST-GONE" not in ceo  # phone_all nhưng không có inactive


def test_danh_ba_tim_khong_phan_biet_dau_va_loc_phong_ban(env):
    get, _ = env
    assert codes(get("TEST-S1", "/api/hr/directory", q="nguyen thi truong").json()["items"], lambda r: r["person"]["code"]) == ["TEST-TP"]
    assert codes(get("TEST-S1", "/api/hr/directory", q="TRẦN QUẢN").json()["items"], lambda r: r["person"]["code"]) == ["TEST-MG"]
    assert [r["person"]["code"] for r in get("TEST-S1", "/api/hr/directory", q="test-s1@test").json()["items"]] == ["TEST-S1"]
    assert get("TEST-S1", "/api/hr/directory", q="TEST%").json()["items"] == []  # % không phải ký tự đại diện
    d = get("TEST-S1", "/api/hr/directory", q="TEST-", department="TKD").json()
    assert codes(d["items"], lambda r: r["person"]["code"]) == ["TEST-X"]
    assert {"TDA", "TKD", "THC", "TBGD", "TIT"} <= set(d["departments"])  # facet không bị lọc theo department


def test_directory_sql_khop_voi_can_view_employee_voi_moi_vai_tro(env):
    """ADR-003 mục 9: hai bản cài độc lập phải cho cùng kết quả, kể cả với nhân viên thật có sẵn trong agent-db."""
    _, db = env
    everyone = db.execute(select(Employee)).scalars().all()
    for code, *_ in ORG:
        p = load_principal(db, email(code))
        via_sql = set(db.execute(select(Employee.code).where(directory_sql(p))).scalars())
        via_py = {e.code for e in everyone if can_view_employee(p, Target.of(e))}
        assert via_sql == via_py, code


def test_che_so_dien_thoai_khop_ban_python(env):
    _, db = env
    phones = dict(db.execute(select(EmployeeContact.employee_code, EmployeeContact.phone)).all())
    for code, *_ in ORG:
        p = load_principal(db, email(code))
        got = {r.person.code: r.phone for r in service.directory(db, p).items}
        for e in db.execute(select(Employee)).scalars():
            if e.code in got:
                expect = phones.get(e.code) if can_view_phone(p, Target.of(e)) else None
                assert got[e.code] == expect, (code, e.code)


# ---------------------------------------------------------------- nạp dữ liệu từ CSV


def test_seed_hr_nap_csv_that_va_chay_lai_khong_nhan_doi(env):
    _, db = env
    hr_dir = Path(__file__).resolve().parents[2] / "data" / "hr"
    rows = (read(hr_dir / "employees.csv"), read(hr_dir / "leave_balances.csv"), read(hr_dir / "leave_requests.csv"))

    def real_counts():  # bỏ dữ liệu TEST- của fixture
        n = lambda col, table: db.scalar(select(func.count()).select_from(table).where(~col.like("TEST-%")))  # noqa: E731
        return (
            n(LeaveBalance.employee_code, LeaveBalance),
            n(LeaveRequest.code, LeaveRequest),
            n(EmployeeContact.employee_code, EmployeeContact),
        )

    load_all(db, *rows)
    db.commit()
    first = real_counts()
    load_all(db, *rows)
    db.commit()
    assert real_counts() == first == (24, 143, 24)

    bal = db.execute(select(LeaveBalance).where(LeaveBalance.employee_code == "NV017")).scalar_one()
    assert (bal.year, bal.remaining) == (2026, 7.5)  # số liệu tiêu chí CTA-AI-011 (ADR-003 T1)
    req = db.execute(select(LeaveRequest).where(LeaveRequest.code == "DP-2026-0137")).scalar_one()
    assert (req.employee_code, req.from_date, req.days, req.status, req.approver_code) == (
        "NV017", date(2026, 12, 21), 3.0, "cho-duyet", "NV006",
    )
    assert db.get(EmployeeContact, "NV001").phone == "0912 754 214"
