"""Bước 5: phân quyền của /api/kb, kiểm qua chuỗi xác thực THẬT (token Zitadel giả + bảng employees).

Chỉ get_db và get_verifier được thay (tests/kb_testkit.py, tests/oidc_testkit.py). Ba lớp kiểm tra:
  1. Hành vi: token đủ loại (thiếu, sai, hết hạn, không phải admin) -> 401/403.
  2. Cấu trúc: MỌI route dưới /api/kb phải đòi cổng admin, kể cả route thêm sau này.
  3. Ranh giới: router không import app.security, backend không bật CORS.
"""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.auth.oidc import get_verifier
from app.main import create_app
from tests.kb_testkit import _kb_db, add_doc, add_employee  # noqa: F401  (_kb_db = fixture kb_db)
from tests.oidc_testkit import Idp, bearer

ADMIN = "test.admin@test.example"
STAFF = "test.staff@test.example"

URL = "/api/kb/documents"
APP_DIR = Path(__file__).resolve().parent.parent / "app"

# (method, path, kwargs) cho đủ 7 thao tác của hợp đồng
CALLS = [
    ("get", URL, {}),
    ("get", f"{URL}/TEST-AZ-1", {}),
    ("get", f"{URL}/TEST-AZ-1/access?email=a@b.vn", {}),
    ("post", URL, {"files": {"file": ("a.md", b"# x", "text/markdown")}}),
    ("post", f"{URL}:reindex", {"json": {"docIds": ["TEST-AZ-1"]}}),
    ("put", f"{URL}/TEST-AZ-1/quarantine", {"json": {"on": True}}),
    ("post", f"{URL}:delete", {"json": {"docIds": ["TEST-AZ-1"]}}),
]
CALL_IDS = [f"{m.upper()} {p.replace(URL, '')}" or m for m, p, _ in CALLS]


@pytest.fixture
def idp():
    return Idp()


@pytest.fixture
def real_auth(kb_db, idp):
    """App với xác thực thật; DB là session rollback có sẵn một admin, một staff và tài liệu TEST-AZ-1."""
    add_employee(kb_db, "TEST-AZ-A", ADMIN, department="CNTT", roles=["admin", "employee"])
    add_employee(kb_db, "TEST-AZ-S", STAFF, department="KD", roles=["employee"])
    add_doc(kb_db, "TEST-AZ-1")
    app = create_app()
    app.dependency_overrides[get_db] = lambda: kb_db
    app.dependency_overrides[get_verifier] = idp.verifier
    return TestClient(app, raise_server_exceptions=False), kb_db, idp


def call(client, spec, headers=None):
    method, path, kw = spec
    return getattr(client, method)(path, headers=headers or {}, **kw)


# ---------------------------------------------------------------- 1. hành vi với token thật

@pytest.mark.parametrize("spec", CALLS, ids=CALL_IDS)
def test_khong_token_401(real_auth, spec):
    assert call(real_auth[0], spec).status_code == 401


@pytest.mark.parametrize("spec", CALLS, ids=CALL_IDS)
def test_staff_403_ke_ca_khi_token_tu_nhan_admin(real_auth, spec):
    """Vai trò lấy từ bảng employees, KHÔNG tin claim vai trò trong token."""
    c, _, idp = real_auth
    honest = idp.token(email=STAFF)
    lying = idp.token(email=STAFF, roles={"admin": {"1": "x"}}, role="admin")
    assert call(c, spec, bearer(honest)).status_code == 403
    assert call(c, spec, bearer(lying)).status_code == 403


@pytest.mark.parametrize("spec", CALLS, ids=CALL_IDS)
def test_admin_qua_cong_phan_quyen(real_auth, spec):
    """Admin thật không bị 401/403 (kết quả nghiệp vụ có thể là 2xx/404/422/207, miễn không chặn quyền)."""
    c, _, idp = real_auth
    assert call(c, spec, bearer(idp.token(email=ADMIN))).status_code not in (401, 403)


@pytest.mark.parametrize("name,make", [
    ("hết hạn", lambda idp: idp.token(email=ADMIN, exp=1)),
    ("sai aud", lambda idp: idp.token(email=ADMIN, aud=["khac"])),
    ("không phải JWT", lambda idp: "khong.phai.jwt"),
    ("JWT HS256 cũ", lambda idp: __import__("jwt").encode({"sub": "1", "role": "admin"}, "k" * 32, "HS256")),
])
def test_token_xau_401(real_auth, name, make):
    c, _, idp = real_auth
    assert c.get(URL, headers=bearer(make(idp))).status_code == 401, name


def test_header_sai_dinh_dang_401(real_auth):
    c, _, idp = real_auth
    token = idp.token(email=ADMIN)
    assert c.get(URL, headers={"Authorization": f"Basic {token}"}).status_code == 401
    assert c.get(URL, headers={"Authorization": token}).status_code == 401  # thiếu "Bearer"
    assert c.get(URL, headers={"Authorization": "Bearer"}).status_code == 401


def test_403_khong_lo_chi_tiet_noi_bo(real_auth):
    c, _, idp = real_auth
    r = c.get(URL, headers=bearer(idp.token(email=STAFF)))
    assert r.status_code == 403 and "TEST-AZ-1" not in r.text and STAFF not in r.text


# ---------------------------------------------------------------- 2. quét: mọi route đều đòi admin

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


# Route dưới /api/kb dành cho MỌI nhân viên (đăng nhập là đủ, kiểm ở test_kb_ask.py).
# Danh sách miễn phải tường minh: route mới ở /api/kb mà không có tên ở đây vẫn bị bắt buộc có cổng admin.
NOT_ADMIN_ROUTES = {("POST", "/api/kb/ask")}


def kb_operations(app) -> list[tuple[str, str]]:
    """Mọi (method, path) dưới /api/kb phải có cổng admin, lấy từ OpenAPI nên tự gồm cả route thêm sau này."""
    paths = app.openapi()["paths"]
    return [
        (m.upper(), p)
        for p, ops in paths.items() if p.startswith("/api/kb")
        for m in ops if m in HTTP_METHODS and (m.upper(), p) not in NOT_ADMIN_ROUTES
    ]


def ungated(app, client, staff_headers) -> list[str]:
    """Route nào không trả 401 khi thiếu token, hoặc không trả 403 khi là staff."""
    bad = []
    for method, path in kb_operations(app):
        url = re.sub(r"\{[^}]+\}", "X", path)
        if client.request(method, url).status_code != 401:
            bad.append(f"{method} {path}: thiếu token không bị 401")
        elif client.request(method, url, headers=staff_headers).status_code != 403:
            bad.append(f"{method} {path}: staff không bị 403")
    return bad


def test_moi_route_kb_deu_dong_admin(real_auth):
    c, _, idp = real_auth
    app = c.app
    assert len(kb_operations(app)) >= 7  # bảo đảm đã quét được route thật, không phải quét rỗng
    assert ungated(app, c, bearer(idp.token(email=STAFF))) == []


def test_bo_quet_bat_duoc_route_ho():
    """Chính bộ quét phải bắt được route thiếu cổng admin, tránh kiểm tra vô hiệu."""
    from fastapi import FastAPI

    app = FastAPI()
    app.get("/api/kb/ho")(lambda: {"ok": True})
    bad = ungated(app, TestClient(app), {})
    assert len(bad) == 1 and "/api/kb/ho" in bad[0]


# ---------------------------------------------------------------- 3. ranh giới

@pytest.mark.parametrize("name", ["api/kb.py", "rag/kb_service.py"])
def test_khong_import_thang_app_security(name):
    src = (APP_DIR / name).read_text(encoding="utf-8")
    direct = re.search(r"^\s*(from|import)\s+app\.security\b", src, re.M)
    assert not direct, f"{name} import thẳng app.security"


def test_router_kb_chi_import_xac_thuc_tu_deps():
    src = (APP_DIR / "api" / "kb.py").read_text(encoding="utf-8")
    assert "from app.api.deps import" in src and "get_kb_admin" in src


def test_khong_bat_cors():
    app = create_app()
    assert not any(m.cls.__name__ == "CORSMiddleware" for m in app.user_middleware)
    r = TestClient(app).options(
        URL, headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"}
    )
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers}
    r = TestClient(app).get("/healthz", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers}


def test_quy_tac_acl_khong_bi_viet_lai():
    """kb_service dùng lại can_read/load_principal của acl.py; không có bản sao quy tắc visibility."""
    from app.rag import acl, kb_service

    assert kb_service.can_read is acl.can_read and kb_service.load_principal is acl.load_principal
    src = (APP_DIR / "rag" / "kb_service.py").read_text(encoding="utf-8")
    assert "acl_sql" not in src and "overlap(" not in src and ".any(" not in src
