"""Kiểm token Zitadel (docs/06 giai đoạn 4, ca 2-4 của ADR-004). Token tự ký bằng khoá RSA sinh trong test.

Phần 1: OidcVerifier thuần (không DB). Phần 2: các endpoint thật qua TestClient, DB là transaction rollback
(tests/kb_testkit.py; không có DB thì skip). Phần 3: knowledge-mcp và get_asker_email.
"""

import jwt
import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_asker_email, get_db
from app.auth.oidc import OidcError, get_verifier
from app.knowledge_mcp import authenticate_headers
from app.main import create_app
from tests.kb_testkit import _kb_db, add_doc, add_employee, audit_since_start  # noqa: F401  (_kb_db = fixture kb_db)
from tests.oidc_testkit import ISSUER, KID, PROJECT_ID, Idp, bearer, new_key

URL = "/api/kb/documents"


@pytest.fixture(name="idp")
def _idp():
    return Idp()


# ---------------------------------------------------------------- 1. OidcVerifier


def test_token_hop_le_tra_email_chuan_hoa(idp):
    ident = idp.verifier().identity(idp.token(email="Binh.Le@Test.Example"))
    assert ident.email == "binh.le@test.example" and ident.sub == "u-1"


def _expect_401(idp, token):
    with pytest.raises(OidcError) as e:
        idp.verifier().identity(token)
    assert e.value.status_code == 401


@pytest.mark.parametrize(
    "name,make",
    [
        ("sai chữ ký (khoá lạ)", lambda i: i.token(key=new_key())),
        ("sai issuer", lambda i: i.token(iss="https://evil.example")),
        ("aud là project khác", lambda i: i.token(aud=["999999", "client-x"])),
        ("không có aud", lambda i: i.token(aud=None)),
        ("hết hạn", lambda i: i.token(exp=1)),
        ("không có exp", lambda i: i.token(exp=None)),
        ("chưa đến nbf", lambda i: i.token(nbf=4_102_444_800)),
        (
            "alg=none",
            lambda i: jwt.encode(
                {"iss": ISSUER, "aud": PROJECT_ID, "sub": "x", "exp": 4_102_444_800},
                None,
                algorithm="none",
                headers={"kid": KID},
            ),
        ),
        (
            "HS256 ký bằng secret của backend",
            lambda i: jwt.encode(
                {"iss": ISSUER, "aud": PROJECT_ID, "sub": "x", "exp": 4_102_444_800},
                "k" * 40,
                algorithm="HS256",
                headers={"kid": KID},
            ),
        ),
        ("không phải JWT", lambda i: "khong.phai.jwt"),
        ("kid lạ", lambda i: i.token(kid="kid-khong-co")),
    ],
)
def test_token_xau_401(idp, name, make):
    _expect_401(idp, make(idp))


def test_hs256_voi_kid_hop_le_van_bi_tu_choi_vi_chi_nhan_rs256(idp):
    """Chống tấn công đổi thuật toán (RS256 -> HS256): kid đúng nhưng alg HS256 phải bị chặn từ đầu."""
    _expect_401(idp, jwt.encode({"sub": "x"}, "k" * 40, algorithm="HS256", headers={"kid": KID}))


def test_email_chua_xac_minh_bi_tu_choi(idp):
    _expect_401(idp, idp.token(email_verified=False))


def test_thieu_email_thi_hoi_userinfo_va_cache(idp):
    idp.userinfo_reply = {"sub": "u-1", "email": "binh.le@test.example", "email_verified": True}
    v = idp.verifier()
    token = idp.token(email=None)
    assert v.identity(token).email == "binh.le@test.example"
    assert v.identity(token).email == "binh.le@test.example"
    assert idp.userinfo_calls == 1  # lần hai lấy từ cache
    idp.now += 301  # quá TTL: hỏi lại, nên token bị thu hồi/khoá tài khoản sẽ lộ ra sau tối đa 5 phút
    v.identity(token)
    assert idp.userinfo_calls == 2


@pytest.mark.parametrize(
    "reply",
    [
        None,  # userinfo báo token không còn hiệu lực
        {"sub": "nguoi-khac", "email": "a@x", "email_verified": True},
        {"sub": "u-1", "email": "a@x", "email_verified": False},
        {"sub": "u-1", "email_verified": True},
    ],
)
def test_userinfo_xau_401(idp, reply):
    idp.userinfo_reply = reply
    _expect_401(idp, idp.token(email=None))


def test_kid_la_chi_tai_lai_khoa_toi_da_mot_lan_moi_30_giay(idp):
    v = idp.verifier()
    for i in range(10):
        with pytest.raises(OidcError):
            v.identity(idp.token(kid=f"kid-gia-{i}"))
    assert idp.fetches == 1  # bị spam kid giả cũng không thành spam tới Zitadel
    idp.now += 31
    with pytest.raises(OidcError):
        v.identity(idp.token(kid="kid-gia-moi"))
    assert idp.fetches == 2


def test_xoay_khoa_kid_moi_duoc_nhan_sau_khi_het_thoi_gian_cho(idp):
    v = idp.verifier()
    assert v.identity(idp.token()).email  # nạp JWKS lần đầu (kid cũ)
    idp.key, idp.kid = new_key(), "kid-2"  # Zitadel xoay khoá
    token = idp.token()
    with pytest.raises(OidcError):
        v.identity(token)  # vừa tải JWKS cách đây chưa tới 30 giây: chưa được tải lại
    idp.now += 31
    assert v.identity(token).email  # tải lại, thấy kid-2
    assert idp.fetches == 2


def test_khong_toi_duoc_zitadel_la_503_khong_phai_500(idp):
    import httpx

    def boom():
        raise httpx.ConnectError("down")

    v = idp.verifier()
    v.keys._fetch = boom
    with pytest.raises(OidcError) as e:
        v.identity(idp.token())
    assert e.value.status_code == 503


# ---------------------------------------------------------------- 2. endpoint thật


@pytest.fixture(name="api")
def _api(kb_db, idp):
    """/api/kb với xác thực THẬT (token Zitadel giả + bảng employees); chỉ get_db và get_verifier bị thay."""
    add_employee(kb_db, "TEST-A", "test.admin@test.example", department="CNTT", roles=["admin", "employee"])
    add_employee(kb_db, "TEST-B", "test.binh@test.example", department="KD", roles=["employee"])
    add_employee(
        kb_db, "TEST-C", "test.cu@test.example", department="CNTT", roles=["admin"], status="da-nghi-viec"
    )
    add_doc(kb_db, "TEST-OIDC-1")
    add_doc(kb_db, "TEST-OIDC-MAT", classification="Mat")
    app = create_app()
    app.dependency_overrides[get_db] = lambda: kb_db
    app.dependency_overrides[get_verifier] = idp.verifier
    return TestClient(app, raise_server_exceptions=False), kb_db


def get(api, token=None):
    c, _ = api
    return c.get(URL, headers=bearer(token) if token else {})


def test_admin_nhan_vien_vao_duoc(api, idp):
    r = get(api, idp.token(email="test.admin@test.example"))
    assert r.status_code == 200 and any(d["docId"] == "TEST-OIDC-1" for d in r.json())


def test_nhan_vien_thuong_403_va_khong_lo_chi_tiet(api, idp):
    r = get(api, idp.token(email="test.binh@test.example"))
    assert r.status_code == 403 and "TEST-OIDC-1" not in r.text


def test_vai_tro_lay_tu_employees_khong_tin_claim_trong_token(api, idp):
    token = idp.token(email="test.binh@test.example", roles={"admin": {"1": "x"}}, role="admin")
    assert get(api, token).status_code == 403


def test_email_khong_co_trong_danh_ba_403_khong_500(api, idp):  # ADR-004 ca 3
    r = get(api, idp.token(email="la.hoac@test.example"))
    assert r.status_code == 403 and "danh bạ" in r.json()["detail"]


def test_nghi_viec_bi_chan_du_token_con_han(api, idp):  # ADR-004 ca 4
    r = get(api, idp.token(email="test.cu@test.example"))
    assert r.status_code == 403 and "không còn hoạt động" in r.json()["detail"]


def test_doi_trang_thai_nhan_vien_co_hieu_luc_ngay_voi_cung_mot_token(api, idp):
    c, db = api
    token = idp.token(email="test.admin@test.example")
    assert get(api, token).status_code == 200
    from sqlalchemy import update

    from app.models import Employee

    db.execute(update(Employee).where(Employee.code == "TEST-A").values(status="da-nghi-viec"))
    db.commit()
    assert get(api, token).status_code == 403


@pytest.mark.parametrize(
    "name,kw",
    [
        ("sai aud", {"aud": ["khac"]}),
        ("sai iss", {"iss": "https://evil.example"}),
        ("hết hạn", {"exp": 1}),
        ("khoá lạ", {"key": "NEW"}),
    ],
)
def test_token_sai_401(api, idp, name, kw):  # ADR-004 ca 2
    kw = {k: (new_key() if v == "NEW" else v) for k, v in kw.items()}
    assert get(api, idp.token(email="test.admin@test.example", **kw)).status_code == 401, name


def test_khong_token_401(api):
    assert get(api).status_code == 401


def test_chua_cau_hinh_oidc_thi_tu_choi_het(kb_db, idp):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: kb_db
    app.dependency_overrides[get_verifier] = lambda: None
    r = TestClient(app).get(URL, headers=bearer(idp.token(email="test.admin@test.example")))
    assert r.status_code == 401


def test_thao_tac_ghi_ghi_email_nguoi_thuc_hien_vao_audit(api, idp):
    c, db = api
    h = bearer(idp.token(email="test.admin@test.example"))
    assert c.put(f"{URL}/TEST-OIDC-1/quarantine", json={"on": True}, headers=h).status_code == 204
    (row,) = audit_since_start(db, "kb_quarantine")
    assert row.user_id is None  # không nhét employee_id vào user_id (khác không gian id với bảng users)
    assert row.detail["actor"] == "test.admin@test.example"
    detail = c.get(f"{URL}/TEST-OIDC-1", headers=h).json()
    assert detail["history"][0]["by"] == "test.admin@test.example"


def test_admin_xem_tai_lieu_mat_van_bi_ghi_log(api, idp):  # ADR-004 ca 6
    c, db = api
    h = bearer(idp.token(email="test.admin@test.example"))
    r = c.get(f"{URL}/TEST-OIDC-MAT", headers=h)
    assert r.status_code == 200 and r.json()["accessLogged"] is True
    (row,) = audit_since_start(db, "kb_view_classified")
    assert row.detail["actor"] == "test.admin@test.example" and row.detail["doc_id"] == "TEST-OIDC-MAT"


def test_jwt_cu_hs256_bi_tu_choi_sau_giai_doan_6(api):
    """JWT HS256 tự phát của backend đã bỏ: không còn đường nào nhận nó."""
    c, _ = api
    legacy = jwt.encode({"sub": "1", "role": "admin"}, "k" * 32, algorithm="HS256")
    assert c.get(URL, headers=bearer(legacy)).status_code == 401


# ---------------------------------------------------------------- 3. get_asker_email và knowledge-mcp


def test_asker_email_tu_bearer_khong_co_cau_noi_cu(idp):
    v = idp.verifier()
    assert get_asker_email(authorization=f"Bearer {idp.token()}", verifier=v) == "binh.le@test.example"
    from fastapi import HTTPException

    for bad in (f"Bearer {idp.token(exp=1)}", "", "Bearer"):
        with pytest.raises(HTTPException) as e:
            get_asker_email(authorization=bad, verifier=v)
        assert e.value.status_code == 401
    with pytest.raises(HTTPException) as e:  # OIDC chưa cấu hình: fail closed
        get_asker_email(authorization=f"Bearer {idp.token()}", verifier=None)
    assert e.value.status_code == 401


def test_mcp_bearer_hop_le(idp):
    email = authenticate_headers({"Authorization": f"Bearer {idp.token()}"}, idp.verifier())
    assert email == "binh.le@test.example"


def test_mcp_bearer_sai_bi_tu_choi_du_co_header_cu(idp):
    h = {
        "Authorization": f"Bearer {idp.token(exp=1)}",
        "X-KB-Token": "bat-ky",
        "X-User-Email": "huy.do@x",
    }
    with pytest.raises(PermissionError):
        authenticate_headers(h, idp.verifier())


@pytest.mark.parametrize("auth", [None, "Bearer {{LIBRECHAT_OPENID_ACCESS_TOKEN}}", "Bearer ", "Basic abc"])
def test_mcp_khong_co_bearer_thi_tu_choi_x_kb_token_da_go(idp, auth):
    """Giai đoạn 6: X-KB-Token + X-User-Email không còn là đường vào, kể cả khi LibreChat chưa thay biến."""
    h = {"x-kb-token": "bat-ky", "x-user-email": "binh.le@test.example"}
    if auth is not None:
        h["authorization"] = auth
    with pytest.raises(PermissionError):
        authenticate_headers(h, idp.verifier())


def test_mcp_bearer_nhung_oidc_chua_cau_hinh_thi_tu_choi(idp):
    with pytest.raises(PermissionError):
        authenticate_headers({"authorization": f"Bearer {idp.token()}"}, None)
