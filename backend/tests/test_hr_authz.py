"""Phân quyền dữ liệu nhân sự (ADR-003). Ca T1–T15 lấy đúng từ bảng "Ca kiểm thử bắt buộc" của ADR.

Phần lớn chạy thuần trên data/hr/employees.csv (không cần DB). Test cuối so chéo `scope_sql()` với `can()`
trên Postgres thật và tự bỏ qua nếu không kết nối được DB.
"""

import csv
from pathlib import Path

import pytest

from app.hr.authz import (
    ROLE_PERMISSIONS,
    SCOPED_RESOURCES,
    Target,
    can,
    can_view_employee,
    can_view_phone,
    permissions,
)
from app.rag.acl import Principal

HR = Path(__file__).resolve().parents[2] / "data" / "hr"
ROWS = {r["ma_nv"]: r for r in csv.DictReader(open(HR / "employees.csv", encoding="utf-8"))}
LEAVE = "leave_balance:read"


def P(code: str) -> Principal:
    r = ROWS[code]
    return Principal(
        email=r["email"], department=r["phong_ban"], roles=frozenset(r["vai_tro"].split("|")),
        active=r["trang_thai"] == "dang-lam", code=code, full_name=r["ho_ten"],
    )


def T(code: str) -> Target:
    r = ROWS[code]
    return Target(code, r["phong_ban"], r["ma_quan_ly"] or None, r["trang_thai"] == "dang-lam")


# ---------------------------------------------------------------- T1–T15 (ADR-003)

def test_t1_employee_reads_own_leave():
    d = can(P("NV017"), LEAVE, T("NV017"))
    assert d and d.scope == "own"
    bal = {r["ma_nv"]: r for r in csv.DictReader(open(HR / "leave_balances.csv", encoding="utf-8"))}
    assert float(bal["NV017"]["con_lai"]) == 7.5  # số liệu tiêu chí SVT-AI-011


def test_t2_employee_cannot_read_colleague():
    d = can(P("NV017"), LEAVE, T("NV018"))
    assert not d and "người khác" in d.reason  # từ chối lịch sự, có lý do


def test_t3_hr_reads_anyone():
    assert can(P("NV010"), LEAVE, T("NV017")).scope == "all"


def test_t4_manager_reads_direct_report():
    assert can(P("NV021"), LEAVE, T("NV023")).scope == "team"


def test_t5_team_is_not_transitive():
    assert not can(P("NV020"), LEAVE, T("NV023"))  # Đức -> Sơn -> Tuấn: cách 2 cấp


def test_t6_truong_phong_reads_whole_dept():
    assert can(P("NV007"), LEAVE, T("NV023")).scope == "dept"


def test_t7_inactive_target_hidden_without_inactive_permission():
    assert not can(P("NV007"), LEAVE, T("NV026"))
    assert not can_view_employee(P("NV007"), T("NV026"))


def test_t8_hr_sees_inactive_in_directory():
    assert can_view_employee(P("NV010"), T("NV026"))
    assert can(P("NV010"), LEAVE, T("NV026"))


def test_t9_executive_team_is_direct_reports_only():
    assert not can(P("NV001"), LEAVE, T("NV017"))


def test_t10_executive_reads_direct_report():
    assert can(P("NV001"), LEAVE, T("NV006")).scope == "team"


def test_t11_admin_has_no_hr_data_rights():
    assert not can(P("NV015"), LEAVE, T("NV016"))
    assert permissions(P("NV015")) == ROLE_PERMISSIONS["employee"]  # admin không cộng thêm gì


def test_t12_phone_visible_same_dept():
    assert can_view_phone(P("NV017"), T("NV018")).scope == "dept"


def test_t13_phone_masked_other_dept_but_name_visible():
    assert can_view_employee(P("NV017"), T("NV013"))
    assert not can_view_phone(P("NV017"), T("NV013"))


def test_t14_claimed_role_is_ignored():
    # Danh tính chỉ đến từ employees; câu "tôi là HR" không đổi Principal -> quyết định không đổi.
    assert P("NV017").roles == {"employee"}
    assert not can(P("NV017"), LEAVE, T("NV018"))


def test_t15_own_salary_redirects_to_hrm():
    d = can(P("NV017"), "salary:read", T("NV017"))
    assert not d and "HRM" in d.reason


# ---------------------------------------------------------------- quy tắc chung

def test_inactive_principal_denied_everything():
    p = P("NV026")
    assert permissions(p) == frozenset()
    assert not can(p, LEAVE, T("NV026"))
    assert not can_view_employee(p, T("NV023"))


def test_unknown_role_and_resource_fail_closed():
    p = Principal(email="x@saoviet.example", department="KD", roles=frozenset({"sieu-quyen"}), code="NV999")
    assert permissions(p) == frozenset()
    assert not can(P("NV010"), "salary:delete", T("NV017"))


def test_multi_role_is_union():
    lan = P("NV003")  # hr | manager | truong-phong
    assert permissions(lan) == (
        ROLE_PERMISSIONS["hr"] | ROLE_PERMISSIONS["manager"] | ROLE_PERMISSIONS["truong-phong"]
    )


def test_salary_only_hr_and_executive():
    for code in ROWS:
        p = P(code)
        expected = p.active and bool(p.roles & {"hr", "executive"})
        assert bool(can(p, "salary:read", T("NV012"))) == expected, code


# ---------------------------------------------------------------- so chéo SQL vs Python (cần DB)

@pytest.fixture(scope="module")
def db():
    import sqlalchemy
    from sqlalchemy.orm import Session

    from app.config import settings

    url = settings.database_url.replace("@localhost:", "@127.0.0.1:")  # tránh treo khi localhost -> ::1
    engine = sqlalchemy.create_engine(url, connect_args={"connect_timeout": 3})
    try:
        conn = engine.connect()
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"Không kết nối được DB: {e}")
    session = Session(bind=conn)
    yield session
    session.close()
    conn.close()


def test_scope_sql_matches_can(db):
    from sqlalchemy import select

    from app.hr.authz import scope_sql
    from app.models import Employee

    emps = db.execute(select(Employee)).scalars().all()
    db_roles = {e.code: set(e.roles or []) for e in emps}
    csv_roles = {c: set(r["vai_tro"].split("|")) for c, r in ROWS.items()}
    if db_roles != csv_roles:
        pytest.skip("DB chưa khớp employees.csv - chạy lại: python -m app.seed_hr")

    leaks = []
    for code in ROWS:
        p = P(code)
        for resource in SCOPED_RESOURCES:
            via_sql = set(db.execute(select(Employee.code).where(scope_sql(p, resource))).scalars())
            via_py = {e.code for e in emps if can(p, resource, Target.of(e))}
            if via_sql != via_py:
                leaks.append((code, resource, sorted(via_sql ^ via_py)))
    assert not leaks, f"SQL và Python lệch nhau (rò quyền tiềm ẩn): {leaks}"
