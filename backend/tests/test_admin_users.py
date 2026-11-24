"""/api/admin/users: tài khoản Zitadel ghép với danh bạ nhân sự.

- Đăng nhập: token Zitadel tự ký (tests/oidc_testkit.py), vai trò tra từ bảng employees như thật.
- Zitadel: bản giả trong bộ nhớ chạy qua httpx.MockTransport, nên KHÔNG có tài khoản thật nào bị tạo hay khoá.
- DB: transaction rollback (tests/kb_testkit.py); nhân viên mang mã/email TEST.
"""

import json
import re

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.deps import get_db
from app.auth.oidc import get_verifier
from app.auth.zitadel_admin import ZitadelAdmin, get_zitadel_admin
from app.main import create_app
from app.models import AuditLog
from tests.kb_testkit import _kb_db, add_employee, audit_since_start  # noqa: F401  (_kb_db = fixture kb_db)
from tests.oidc_testkit import Idp, bearer

ADMIN = "test.qtv@test.example"
STAFF = "test.nv@test.example"


class FakeZitadel:
    """Đủ các endpoint User Service mà client dùng. `calls` ghi lại (method, path) để kiểm không gọi thừa."""

    def __init__(self) -> None:
        self.users: dict[str, dict] = {}
        self.calls: list[tuple[str, str]] = []
        self.passwords: dict[str, dict] = {}
        self.created: list[dict] = []
        self.fail_writes = False
        self._next = 1000
        self.add("1", "portal-admin-api", state="USER_STATE_ACTIVE", human=False)  # machine user: không được lộ ra

    def add(self, uid: str, email: str, *, state="USER_STATE_ACTIVE", human=True, name="") -> None:
        u = {"userId": uid, "username": email, "state": state}
        if human:
            u["human"] = {"email": {"email": email, "isVerified": True}, "profile": {"displayName": name or email}}
        else:
            u["machine"] = {"name": email}
        self.users[uid] = u

    def client(self) -> ZitadelAdmin:
        return ZitadelAdmin("http://z", "pat", host="auth.test.example", transport=httpx.MockTransport(self.handle))

    def handle(self, req: httpx.Request) -> httpx.Response:
        path, method = req.url.path, req.method
        self.calls.append((method, path))
        body = json.loads(req.content) if req.content else {}
        if method == "POST" and path == "/v2/users":
            q = body.get("queries", [{}])[0]
            if "userNameQuery" in q:
                name = q["userNameQuery"]["userName"]
                return httpx.Response(200, json={"result": [u for u in self.users.values() if u["username"] == name]})
            rows = [u for u in self.users.values() if "human" in u]
            off, lim = body["query"]["offset"], body["query"]["limit"]
            return httpx.Response(200, json={"result": rows[off : off + lim]})
        if method == "GET" and (m := re.fullmatch(r"/v2/users/(\w+)", path)):
            u = self.users.get(m.group(1))
            return httpx.Response(200, json={"user": u}) if u else httpx.Response(404, json={"message": "no"})
        if method == "POST" and path == "/v2/users/human":
            if self.fail_writes:
                return httpx.Response(500, text="boom: internal secret detail")
            self._next += 1
            uid = str(self._next)
            self.created.append(body)
            self.add(uid, body["username"], name=body["profile"]["displayName"])
            self.passwords[uid] = body["password"]
            return httpx.Response(201, json={"userId": uid})
        if method == "POST" and (m := re.fullmatch(r"/v2/users/(\w+)/(deactivate|reactivate|password)", path)):
            uid, action = m.groups()
            if self.fail_writes:
                return httpx.Response(500, text="boom: internal secret detail")
            if action == "password":
                self.passwords[uid] = body["newPassword"]
            else:
                self.users[uid]["state"] = "USER_STATE_INACTIVE" if action == "deactivate" else "USER_STATE_ACTIVE"
            return httpx.Response(200, json={})
        return httpx.Response(404, json={"message": f"unhandled {method} {path}"})

    def writes(self) -> list[tuple[str, str]]:
        return [c for c in self.calls if c[0] == "POST" and c[1] != "/v2/users"]


@pytest.fixture(name="env")
def _env(kb_db):
    idp, fake = Idp(), FakeZitadel()
    add_employee(kb_db, "TEST-QT", ADMIN, roles=["admin"], name="Quản Trị Thử")
    add_employee(kb_db, "TEST-NV", STAFF, roles=["employee"], name="Nhân Viên Thử")
    app = create_app()
    app.dependency_overrides[get_db] = lambda: kb_db
    app.dependency_overrides[get_verifier] = idp.verifier
    app.dependency_overrides[get_zitadel_admin] = fake.client
    client = TestClient(app, raise_server_exceptions=False)
    admin_h = bearer(idp.token(email=ADMIN, sub="u-admin"))
    return client, kb_db, fake, admin_h, idp


# ---------------------------------------------------------------- quyền


def test_can_token_va_vai_tro_admin(env):
    c, _, fake, admin_h, idp = env
    assert c.get("/api/admin/users").status_code == 401
    staff_h = bearer(idp.token(email=STAFF, sub="u-staff"))
    for method, path in (
        ("get", "/api/admin/users"),
        ("post", "/api/admin/users"),
        ("post", "/api/admin/users/5/deactivate"),
        ("post", "/api/admin/users/5/reactivate"),
        ("post", "/api/admin/users/5/password"),
    ):
        r = c.request(method.upper(), path, headers=staff_h, json={"email": STAFF} if method == "post" else None)
        assert r.status_code == 403, path
    assert fake.calls == []  # nhân viên thường không chạm tới Zitadel
    assert c.get("/api/admin/users", headers=admin_h).status_code == 200


def test_chua_cau_hinh_zitadel_thi_503(env):
    c, _, _, admin_h, _ = env
    c.app.dependency_overrides[get_zitadel_admin] = lambda: None
    r = c.get("/api/admin/users", headers=admin_h)
    assert r.status_code == 503 and "ZITADEL_ADMIN_PAT" in r.json()["detail"]


# ---------------------------------------------------------------- danh sách


def test_danh_sach_ghep_nhan_vien_voi_tai_khoan(env):
    c, db, fake, admin_h, _ = env
    add_employee(db, "TEST-U1", "test.u1@test.example", name="Có Tài Khoản")
    add_employee(db, "TEST-U2", "test.u2@test.example", name="Chưa Có Tài Khoản")
    add_employee(db, "TEST-U3", "test.u3@test.example", name="Đã Nghỉ Còn Tk", status="da-nghi-viec")
    add_employee(db, "TEST-U4", "test.u4@test.example", name="Đã Nghỉ Đã Khoá", status="da-nghi-viec")
    fake.add("11", "test.u1@test.example", name="Có Tài Khoản")
    fake.add("13", "test.u3@test.example")
    fake.add("14", "test.u4@test.example", state="USER_STATE_INACTIVE")
    fake.add("15", "test.la@test.example", name="Người Lạ")  # không có trong danh bạ
    fake.add("16", "test.khoa@test.example", state="USER_STATE_LOCKED")

    items = {i["email"]: i for i in c.get("/api/admin/users", headers=admin_h).json()["items"]}
    assert "portal-admin-api" not in {i["email"] for i in items.values()}  # machine user không lộ

    u1 = items["test.u1@test.example"]
    assert (u1["account"], u1["zitadelId"], u1["warning"], u1["employee"]["code"]) == ("active", "11", None, "TEST-U1")
    u2 = items["test.u2@test.example"]
    assert (u2["account"], u2["zitadelId"], u2["warning"], u2["key"]) == ("none", None, None, "e:TEST-U2")
    assert items["test.u3@test.example"]["warning"] == "Đã nghỉ việc nhưng tài khoản còn mở."
    u4 = items["test.u4@test.example"]
    assert (u4["account"], u4["warning"], u4["employee"]["active"]) == ("inactive", None, False)
    la = items["test.la@test.example"]
    assert la["employee"] is None and la["account"] == "active" and "danh bạ" in la["warning"]
    assert items["test.khoa@test.example"]["account"] == "locked"
    assert fake.writes() == []  # chỉ đọc


# ---------------------------------------------------------------- tạo


def test_tao_tai_khoan_ghi_audit_va_chi_tra_mat_khau_mot_lan(env):
    c, db, fake, admin_h, _ = env
    add_employee(db, "TEST-N1", "Test.N1@test.example", name="Lê Văn Mới", department="KD")
    r = c.post("/api/admin/users", headers=admin_h, json={"email": " TEST.n1@test.example "})
    assert r.status_code == 201 and r.headers["cache-control"] == "no-store"
    d = r.json()
    pw = d["tempPassword"]
    assert len(pw) >= 10 and d["user"]["account"] == "active" and d["user"]["employee"]["code"] == "TEST-N1"

    sent = fake.created[0]
    assert sent["username"] == "test.n1@test.example" and sent["email"] == {"email": "test.n1@test.example", "isVerified": True}
    assert sent["password"] == {"password": pw, "changeRequired": True}
    assert sent["profile"]["displayName"] == "Lê Văn Mới"  # tên lấy từ danh bạ, không do client gửi

    (row,) = audit_since_start(db, "user_create")
    assert row.user_id is None and row.detail == {"actor": ADMIN, "target": "test.n1@test.example"}
    assert pw not in json.dumps(row.detail)


@pytest.mark.parametrize(
    ("email", "status"),
    [
        ("test.khong.co@test.example", 422),  # không có trong danh bạ
        ("khong-phai-email", 422),
        ("test.cu@test.example", 409),  # đã nghỉ việc
        ("test.co.san@test.example", 409),  # đã có tài khoản
    ],
)
def test_tao_tai_khoan_bi_tu_choi_khong_cham_zitadel_va_khong_audit(env, email, status):
    c, db, fake, admin_h, _ = env
    add_employee(db, "TEST-CU", "test.cu@test.example", status="da-nghi-viec")
    add_employee(db, "TEST-CS", "test.co.san@test.example")
    fake.add("77", "test.co.san@test.example")
    r = c.post("/api/admin/users", headers=admin_h, json={"email": email})
    assert r.status_code == status, r.text
    assert fake.writes() == [] and audit_since_start(db, "user_create") == []


def test_zitadel_loi_thi_502_cau_chung_va_khong_audit(env):
    c, db, fake, admin_h, _ = env
    add_employee(db, "TEST-N2", "test.n2@test.example")
    fake.fail_writes = True
    r = c.post("/api/admin/users", headers=admin_h, json={"email": "test.n2@test.example"})
    assert r.status_code == 502 and "boom" not in r.text and "secret" not in r.text
    assert audit_since_start(db, "user_create") == []  # việc chưa xảy ra thì không có dòng audit


# ---------------------------------------------------------------- khoá / mở / đặt lại mật khẩu


def test_khoa_va_mo_khoa_ghi_audit(env):
    c, db, fake, admin_h, _ = env
    add_employee(db, "TEST-K1", "test.k1@test.example")
    fake.add("21", "test.k1@test.example")

    r = c.post("/api/admin/users/21/deactivate", headers=admin_h)
    assert r.status_code == 200 and r.json()["account"] == "inactive"
    assert fake.users["21"]["state"] == "USER_STATE_INACTIVE"
    assert c.post("/api/admin/users/21/deactivate", headers=admin_h).status_code == 409  # đã khoá

    r = c.post("/api/admin/users/21/reactivate", headers=admin_h)
    assert r.status_code == 200 and r.json()["account"] == "active"
    assert c.post("/api/admin/users/21/reactivate", headers=admin_h).status_code == 409  # đang hoạt động

    (d,) = audit_since_start(db, "user_deactivate")
    (a,) = audit_since_start(db, "user_reactivate")
    assert d.detail == {"actor": ADMIN, "target": "test.k1@test.example"} and a.detail == d.detail
    assert len(fake.writes()) == 2  # hai lần bị từ chối không gọi ghi


def test_khong_tu_khoa_chinh_minh(env):
    c, db, fake, admin_h, _ = env
    fake.add("30", ADMIN)
    r = c.post("/api/admin/users/30/deactivate", headers=admin_h)
    assert r.status_code == 409 and "chính mình" in r.json()["detail"]
    assert fake.users["30"]["state"] == "USER_STATE_ACTIVE" and audit_since_start(db, "user_deactivate") == []


@pytest.mark.parametrize("user_id", ["1", "999", "abc", "12x", "٣٣"])
def test_id_la_hoac_machine_user_thi_404_va_khong_bi_khoa(env, user_id):
    c, db, fake, admin_h, _ = env
    for action in ("deactivate", "reactivate", "password"):
        assert c.post(f"/api/admin/users/{user_id}/{action}", headers=admin_h).status_code == 404
    assert fake.users["1"]["state"] == "USER_STATE_ACTIVE"  # portal-admin-api còn nguyên
    assert fake.writes() == []
    if not user_id.isdigit() or not user_id.isascii():
        assert all(not p.endswith(user_id) for _, p in fake.calls)  # id không phải số không được ghép vào đường dẫn


def test_dat_lai_mat_khau_tam(env):
    c, db, fake, admin_h, _ = env
    add_employee(db, "TEST-P1", "test.p1@test.example")
    fake.add("41", "test.p1@test.example")
    r = c.post("/api/admin/users/41/password", headers=admin_h)
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    pw = r.json()["tempPassword"]
    assert fake.passwords["41"] == {"password": pw, "changeRequired": True}
    (row,) = audit_since_start(db, "user_password_reset")
    assert row.detail == {"actor": ADMIN, "target": "test.p1@test.example"} and pw not in json.dumps(row.detail)

    fake.add("42", "test.p2@test.example", state="USER_STATE_INACTIVE")
    assert c.post("/api/admin/users/42/password", headers=admin_h).status_code == 409  # phải mở khoá trước
    assert "42" not in fake.passwords


def test_su_kien_hien_trong_trang_nhat_ky_khong_lo_mat_khau(env):
    c, db, fake, admin_h, _ = env
    add_employee(db, "TEST-A1", "test.a1@test.example")
    c.post("/api/admin/users", headers=admin_h, json={"email": "test.a1@test.example"})
    pw = fake.created[0]["password"]["password"]
    r = c.get("/api/admin/audit", headers=admin_h, params={"event": "user_create"})
    top = r.json()["items"][0]
    assert top["actor"] == ADMIN and top["summary"] == "test.a1@test.example" and top["label"] == "Tạo tài khoản"
    assert pw not in r.text
    assert db.execute(select(AuditLog).where(AuditLog.event == "user_create")).scalars().first() is not None
