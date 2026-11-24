"""Khởi tạo cấu hình Zitadel cho SVT (docs/06 giai đoạn 2.1-2.5). CHẠY LẠI ĐƯỢC NHIỀU LẦN.

Zitadel không export cấu hình ra file như realm của Keycloak, nên script này là "nguồn sự thật":
đọc trạng thái hiện có, chỉ sửa chỗ khác với mong muốn, không tạo trùng.

    cd backend
    .\\.venv\\Scripts\\python ..\\infra\\zitadel\\bootstrap.py            # áp cấu hình
    .\\.venv\\Scripts\\python ..\\infra\\zitadel\\bootstrap.py --dry-run  # chỉ báo sẽ đổi gì

Cần PAT của machine user `bootstrap` (IAM_OWNER, do Zitadel tự tạo lần khởi tạo đầu):
mặc định đọc librechat/zitadel-bootstrap/bootstrap.pat, hoặc đặt ZITADEL_BOOTSTRAP_PAT.

Kết quả (client id/secret, project id, PAT của portal-admin-api) ghi vào infra/zitadel/out/generated.json,
đã .gitignore. Client secret và PAT chỉ được Zitadel trả MỘT LẦN lúc tạo; nếu file mất mà app/user đã
tồn tại, script sinh secret/PAT mới (và báo rõ).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent / "out"
OUT_FILE = OUT_DIR / "generated.json"

# Zitadel chọn instance theo header Host; domain ngoài phải khớp ZITADEL_EXTERNALDOMAIN trong compose.
BASE_URL = os.environ.get("ZITADEL_URL", "http://127.0.0.1:8180")
EXTERNAL_HOST = os.environ.get("ZITADEL_HOST", "auth.tranduyai.id.vn")
PAT_FILE = Path(
    os.environ.get("ZITADEL_BOOTSTRAP_PAT_FILE", ROOT / "librechat" / "zitadel-bootstrap" / "bootstrap.pat")
)

PROJECT_NAME = "svt"
LIBRECHAT_ADMIN_ROLE = "librechat-admin"  # ADR-004 mục 3: vai trò Zitadel duy nhất, chỉ để quản trị LibreChat
MACHINE_USER = "portal-admin-api"
MACHINE_ROLE = "ORG_USER_MANAGER"  # chỉ quản lý user, không quyền gì khác (docs/06 2.4)
PAT_EXPIRES = os.environ.get("ZITADEL_PAT_EXPIRES", "2027-12-31T00:00:00Z")

EMPLOYEES_CSV = ROOT / "data" / "hr" / "employees.csv"

# LibreChat đọc vai trò admin bằng lodash `get`, chỉ nhận MẢNG hoặc chuỗi. Zitadel đặt vai trò
# trong claim `urn:zitadel:iam:org:project:roles` dạng OBJECT {roleKey: {orgId: domain}} nên không khớp.
# Action này thêm claim `roles` dạng mảng role key vào ID token, userinfo và access token.
ROLES_ACTION = "addRolesClaim"
ROLES_ACTION_SCRIPT = """function addRolesClaim(ctx, api) {
  if (ctx.v1.user.grants == undefined || ctx.v1.user.grants.count == 0) {
    return;
  }
  var roles = [];
  ctx.v1.user.grants.grants.forEach(function (grant) {
    grant.roles.forEach(function (role) {
      if (roles.indexOf(role) < 0) {
        roles.push(role);
      }
    });
  });
  api.v1.claims.setClaim('roles', roles);
}
"""
# Flow "Complement Token" (id 2): trigger 4 = trước khi tạo userinfo/ID token, 5 = trước khi tạo access token.
FLOW_COMPLEMENT_TOKEN = 2
TRIGGERS = {4: "PRE_USERINFO_CREATION", 5: "PRE_ACCESS_TOKEN_CREATION"}

CHAT_URL = "https://chat.tranduyai.id.vn"
PORTAL_URL = "https://portal.tranduyai.id.vn"

# --- Chính sách (mức instance; chỉ có một organization nên đủ) ---------------------------------
LOGIN_POLICY = {
    "allowUsernamePassword": True,
    "allowRegister": False,  # chỉ admin được tạo tài khoản
    "allowExternalIdp": False,  # không đăng nhập qua Google/GitHub...
    "forceMfa": False,
    "forceMfaLocalOnly": False,
    "passwordlessType": "PASSWORDLESS_TYPE_NOT_ALLOWED",
    "hidePasswordReset": False,
    "ignoreUnknownUsernames": True,  # không lộ "tài khoản này có tồn tại không"
    "allowDomainDiscovery": False,
    "disableLoginWithEmail": False,
    "disableLoginWithPhone": True,
}
LOCKOUT_POLICY = {"maxPasswordAttempts": 5, "maxOtpAttempts": 5}
PASSWORD_COMPLEXITY = {
    "minLength": 10,
    "hasUppercase": True,
    "hasLowercase": True,
    "hasNumber": True,
    "hasSymbol": True,
}
OIDC_SETTINGS = {
    "accessTokenLifetime": "900s",  # 15 phút
    "idTokenLifetime": "900s",
    "refreshTokenIdleExpiration": "28800s",  # 8 giờ không dùng thì hết
    "refreshTokenExpiration": "604800s",  # tối đa 7 ngày
}

# --- Ứng dụng OIDC trong project `svt` -------------------------------------------------------
_COMMON_APP = {
    "responseTypes": ["OIDC_RESPONSE_TYPE_CODE"],
    "grantTypes": ["OIDC_GRANT_TYPE_AUTHORIZATION_CODE", "OIDC_GRANT_TYPE_REFRESH_TOKEN"],
    "appType": "OIDC_APP_TYPE_WEB",
    "authMethodType": "OIDC_AUTH_METHOD_TYPE_BASIC",  # có client secret + PKCE ở phía client
    "version": "OIDC_VERSION_1_0",
    "devMode": True,  # cho phép redirect http://localhost (dev); prod vẫn dùng https
    "accessTokenType": "OIDC_TOKEN_TYPE_JWT",  # mặc định là opaque, FastAPI cần JWT để tự kiểm chữ ký
    "accessTokenRoleAssertion": True,
    "idTokenRoleAssertion": True,
    "idTokenUserinfoAssertion": True,  # đưa email... vào ID token
}
APPS = {
    "librechat": {
        **_COMMON_APP,
        "redirectUris": [f"{CHAT_URL}/oauth/openid/callback", "http://localhost:3080/oauth/openid/callback"],
        "postLogoutRedirectUris": [CHAT_URL, "http://localhost:3080"],
    },
    "portal": {
        **_COMMON_APP,
        "redirectUris": [
            f"{PORTAL_URL}/api/auth/callback/zitadel",
            "http://localhost:3100/api/auth/callback/zitadel",
        ],
        "postLogoutRedirectUris": [PORTAL_URL, "http://localhost:3100"],
    },
}

ZERO_ENUMS = {
    "PASSWORDLESS_TYPE_NOT_ALLOWED",
    "OIDC_APP_TYPE_WEB",
    "OIDC_AUTH_METHOD_TYPE_BASIC",
    "OIDC_VERSION_1_0",
}
DRY = False

if hasattr(sys.stdout, "reconfigure"):  # console Windows mặc định cp1252, không in được tiếng Việt
    sys.stdout.reconfigure(encoding="utf-8")


def say(tag: str, msg: str) -> None:
    print(f"[{tag:>6}] {msg}")


class Api:
    def __init__(self, token: str) -> None:
        self.c = httpx.Client(
            base_url=BASE_URL, headers={"Host": EXTERNAL_HOST, "Authorization": f"Bearer {token}"}, timeout=30
        )

    def call(self, method: str, path: str, body: dict | None = None) -> dict[str, Any]:
        r = self.c.request(method, path, json=body)
        if (
            method == "PUT"
            and r.status_code == 400
            and ("No changes" in r.text or "not been changed" in r.text)
        ):
            return {}  # đã đúng giá trị mong muốn: Zitadel báo lỗi thay vì bỏ qua
        if r.status_code >= 400:
            raise SystemExit(f"{method} {path} -> {r.status_code}: {r.text[:500]}")
        return r.json() if r.content else {}


def seconds(v: str) -> int:
    return int(str(v).rstrip("s"))


def differs(current: dict, desired: dict) -> dict:
    """Các trường mong muốn khác giá trị hiện có (so cả mảng theo tập hợp, thời lượng theo giây)."""
    diff = {}
    for k, want in desired.items():
        have = current.get(k)
        if isinstance(want, list):
            same = set(have or []) == set(want)
        elif isinstance(want, str) and want.endswith("s") and want[:-1].isdigit():
            same = have is not None and seconds(have) == seconds(want)
        elif isinstance(want, bool):
            same = bool(have) == want  # proto3 bỏ trường false khỏi JSON
        elif isinstance(want, int):
            same = int(have or 0) == want
        else:
            same = have == want
        if not same and have is None and want in ZERO_ENUMS:
            same = True  # giá trị enum đầu tiên (=0) bị proto3 bỏ khỏi JSON
        if not same:
            diff[k] = want
    return diff


def ensure_policy(
    api: Api, name: str, path: str, desired: dict, key: str = "policy", put_path: str | None = None
) -> None:
    cur = api.call("GET", path).get(key, {})
    diff = differs(cur, desired)
    if not diff:
        say("ok", f"chính sách {name}: đã đúng")
        return
    say("đổi", f"chính sách {name}: {sorted(diff)}")
    if DRY:
        return
    # PUT thay cả bản ghi: lấy giá trị hiện có làm nền để không làm rơi các thời lượng khác.
    base = {k: v for k, v in cur.items() if k not in ("details", "isDefault")}
    api.call("PUT", put_path or path, {**base, **desired})


def ensure_project(api: Api, out: dict) -> str:
    q = {"queries": [{"nameQuery": {"name": PROJECT_NAME, "method": "TEXT_QUERY_METHOD_EQUALS"}}]}
    found = api.call("POST", "/management/v1/projects/_search", q).get("result", [])
    # Bật assert roles để vai trò vào token; không bắt buộc mọi người phải có vai trò (hasProjectCheck=false).
    desired = {"projectRoleAssertion": True, "projectRoleCheck": False, "hasProjectCheck": False}
    if not found:
        say("tạo", f"project {PROJECT_NAME}")
        if DRY:
            return "<dry-run>"
        pid = api.call("POST", "/management/v1/projects", {"name": PROJECT_NAME, **desired})["id"]
    else:
        pid = found[0]["id"]
        cur = api.call("GET", f"/management/v1/projects/{pid}")["project"]
        diff = differs(cur, desired)
        if diff:
            say("đổi", f"project {PROJECT_NAME}: {sorted(diff)}")
            if not DRY:
                api.call("PUT", f"/management/v1/projects/{pid}", {"name": PROJECT_NAME, **desired})
        else:
            say("ok", f"project {PROJECT_NAME}: đã đúng (id {pid})")
    out["projectId"] = pid
    return pid


def ensure_role(api: Api, pid: str) -> None:
    q = {"queries": [{"keyQuery": {"key": LIBRECHAT_ADMIN_ROLE, "method": "TEXT_QUERY_METHOD_EQUALS"}}]}
    found = api.call("POST", f"/management/v1/projects/{pid}/roles/_search", q).get("result", [])
    if found:
        say("ok", f"role {LIBRECHAT_ADMIN_ROLE}: đã có")
        return
    say("tạo", f"role {LIBRECHAT_ADMIN_ROLE}")
    if not DRY:
        api.call(
            "POST",
            f"/management/v1/projects/{pid}/roles",
            {"roleKey": LIBRECHAT_ADMIN_ROLE, "displayName": "Quản trị LibreChat", "group": "librechat"},
        )


def ensure_app(api: Api, pid: str, name: str, desired: dict, out: dict) -> None:
    clients = out.setdefault("clients", {})
    q = {"queries": [{"nameQuery": {"name": name, "method": "TEXT_QUERY_METHOD_EQUALS"}}]}
    found = api.call("POST", f"/management/v1/projects/{pid}/apps/_search", q).get("result", [])
    if not found:
        say("tạo", f"app {name}")
        if DRY:
            return
        res = api.call("POST", f"/management/v1/projects/{pid}/apps/oidc", {"name": name, **desired})
        clients[name] = {"clientId": res["clientId"], "clientSecret": res["clientSecret"]}
        return
    app = found[0]
    aid = app["id"]
    cfg = api.call("GET", f"/management/v1/projects/{pid}/apps/{aid}")["app"]["oidcConfig"]
    diff = differs(cfg, desired)
    if diff:
        say("đổi", f"app {name}: {sorted(diff)}")
        if not DRY:
            api.call("PUT", f"/management/v1/projects/{pid}/apps/{aid}/oidc_config", desired)
    else:
        say("ok", f"app {name}: đã đúng")
    entry = clients.setdefault(name, {})
    entry["clientId"] = cfg["clientId"]
    if not entry.get("clientSecret"):
        say("MỚI", f"app {name}: chưa có client secret trong {OUT_FILE.name}, sinh secret mới")
        if not DRY:
            res = api.call(
                "POST", f"/management/v1/projects/{pid}/apps/{aid}/oidc_config/_generate_client_secret", {}
            )
            entry["clientSecret"] = res["clientSecret"]


def ensure_machine_user(api: Api, out: dict) -> None:
    q = {"queries": [{"userNameQuery": {"userName": MACHINE_USER, "method": "TEXT_QUERY_METHOD_EQUALS"}}]}
    found = api.call("POST", "/management/v1/users/_search", q).get("result", [])
    if found:
        uid = found[0]["id"]
        say("ok", f"machine user {MACHINE_USER}: đã có")
    else:
        say("tạo", f"machine user {MACHINE_USER}")
        if DRY:
            return
        uid = api.call(
            "POST",
            "/management/v1/users/machine",
            {
                "userName": MACHINE_USER,
                "name": MACHINE_USER,
                "description": "Backend gọi User Service để quản lý tài khoản (chỉ ORG_USER_MANAGER)",
                "accessTokenType": "ACCESS_TOKEN_TYPE_BEARER",
            },
        )["userId"]
    out["machineUserId"] = uid
    # Quyền: đúng một role org, không thêm.
    members = api.call("POST", "/management/v1/orgs/me/members/_search", {}).get("result", [])
    mine = next((m for m in members if m["userId"] == uid), None)
    if mine is None:
        say("tạo", f"gán {MACHINE_ROLE} cho {MACHINE_USER}")
        if not DRY:
            api.call("POST", "/management/v1/orgs/me/members", {"userId": uid, "roles": [MACHINE_ROLE]})
    elif set(mine.get("roles", [])) != {MACHINE_ROLE}:
        say("đổi", f"quyền của {MACHINE_USER}: {mine.get('roles')} -> [{MACHINE_ROLE}]")
        if not DRY:
            api.call("PUT", f"/management/v1/orgs/me/members/{uid}", {"roles": [MACHINE_ROLE]})
    else:
        say("ok", f"quyền {MACHINE_USER}: chỉ {MACHINE_ROLE}")
    if not out.get("portalAdminApiPat"):
        say("MỚI", f"PAT của {MACHINE_USER}: chưa có trong {OUT_FILE.name}, tạo mới")
        if not DRY:
            out["portalAdminApiPat"] = api.call(
                "POST", f"/management/v1/users/{uid}/pats", {"expirationDate": PAT_EXPIRES}
            )["token"]
    else:
        say("ok", f"PAT của {MACHINE_USER}: đã có trong {OUT_FILE.name}")


def ensure_roles_action(api: Api) -> None:
    q = {"queries": [{"actionNameQuery": {"name": ROLES_ACTION, "method": "TEXT_QUERY_METHOD_EQUALS"}}]}
    found = api.call("POST", "/management/v1/actions/_search", q).get("result", [])
    desired = {"name": ROLES_ACTION, "script": ROLES_ACTION_SCRIPT, "timeout": "10s", "allowedToFail": True}
    if not found:
        say("tạo", f"action {ROLES_ACTION}")
        if DRY:
            return
        action_id = api.call("POST", "/management/v1/actions", desired)["id"]
    else:
        action_id = found[0]["id"]
        if found[0].get("script", "").strip() != ROLES_ACTION_SCRIPT.strip():
            say("đổi", f"action {ROLES_ACTION}: script")
            if not DRY:
                api.call("PUT", f"/management/v1/actions/{action_id}", desired)
        else:
            say("ok", f"action {ROLES_ACTION}: đã đúng")
    flow = api.call("GET", f"/management/v1/flows/{FLOW_COMPLEMENT_TOKEN}").get("flow", {})
    bound = {
        int(t["triggerType"]["id"]): [a["id"] for a in t.get("actions", [])]
        for t in flow.get("triggerActions", [])
    }
    for trigger_id, trigger_name in TRIGGERS.items():
        if bound.get(trigger_id) == [action_id]:
            say("ok", f"flow Complement Token / {trigger_name}: đã gắn {ROLES_ACTION}")
            continue
        say("đổi", f"flow Complement Token / {trigger_name}: gắn {ROLES_ACTION}")
        if not DRY:
            api.call(
                "POST",
                f"/management/v1/flows/{FLOW_COMPLEMENT_TOKEN}/trigger/{trigger_id}",
                {"actionIds": [action_id]},
            )


def admin_emails() -> set[str]:
    """Email nhân viên đang làm việc có vai trò `admin` trong danh bạ (nguồn duy nhất của quyền admin)."""
    with open(EMPLOYEES_CSV, encoding="utf-8") as f:
        return {
            r["email"].strip().lower()
            for r in csv.DictReader(f)
            if "admin" in r["vai_tro"].split("|") and r["trang_thai"] == "dang-lam"
        }


def ensure_admin_grants(api: Api, pid: str) -> None:
    """Chỉ những nhân viên admin mới có role `librechat-admin`; ai có mà không còn là admin thì bị thu hồi."""
    wanted = admin_emails()
    q = {"queries": [{"projectIdQuery": {"projectId": pid}}]}
    grants = api.call("POST", "/management/v1/users/grants/_search", q).get("result", [])
    have: dict[str, dict] = {}
    for g in grants:
        have[g["userName"].lower()] = g
    for email in sorted(wanted):
        g = have.get(email)
        if g and set(g.get("roleKeys", [])) == {LIBRECHAT_ADMIN_ROLE}:
            say("ok", f"quyền {LIBRECHAT_ADMIN_ROLE}: {email}")
            continue
        user = api.call(
            "POST",
            "/management/v1/users/_search",
            {"queries": [{"userNameQuery": {"userName": email, "method": "TEXT_QUERY_METHOD_EQUALS"}}]},
        ).get("result", [])
        if not user:
            say(
                "bỏ",
                f"{email}: chưa có tài khoản Zitadel (chạy backend: python -m app.seed_zitadel rồi chạy lại)",
            )
            continue
        uid = user[0]["id"]
        say("tạo" if g is None else "đổi", f"quyền {LIBRECHAT_ADMIN_ROLE}: {email}")
        if DRY:
            continue
        if g is None:
            api.call(
                "POST",
                f"/management/v1/users/{uid}/grants",
                {"projectId": pid, "roleKeys": [LIBRECHAT_ADMIN_ROLE]},
            )
        else:
            api.call(
                "PUT", f"/management/v1/users/{uid}/grants/{g['id']}", {"roleKeys": [LIBRECHAT_ADMIN_ROLE]}
            )
    for email, g in have.items():
        if email not in wanted:
            say("thu hồi", f"quyền {LIBRECHAT_ADMIN_ROLE}: {email} (không còn là admin)")
            if not DRY:
                api.call("DELETE", f"/management/v1/users/{g['userId']}/grants/{g['id']}")


def load_pat() -> str:
    pat = os.environ.get("ZITADEL_BOOTSTRAP_PAT") or (
        PAT_FILE.read_text().strip() if PAT_FILE.exists() else ""
    )
    if not pat:
        raise SystemExit(
            f"Không thấy PAT của machine user bootstrap ({PAT_FILE}); đặt ZITADEL_BOOTSTRAP_PAT."
        )
    return pat


def main() -> None:
    global DRY
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="chỉ in thay đổi, không ghi gì")
    DRY = ap.parse_args().dry_run

    api = Api(load_pat())
    out: dict = json.loads(OUT_FILE.read_text("utf-8")) if OUT_FILE.exists() else {}

    org = api.call("GET", "/management/v1/orgs/me")["org"]
    say("info", f"organization {org['name']} ({org['id']}) tại {EXTERNAL_HOST}")
    out["orgId"] = org["id"]

    ensure_policy(api, "đăng nhập", "/admin/v1/policies/login", LOGIN_POLICY)
    # Zitadel đặt đường GET và PUT của chính sách này khác nhau (GET .../lockout, PUT .../password/lockout).
    ensure_policy(
        api,
        "khoá tài khoản",
        "/admin/v1/policies/lockout",
        LOCKOUT_POLICY,
        put_path="/admin/v1/policies/password/lockout",
    )
    ensure_policy(api, "độ phức tạp mật khẩu", "/admin/v1/policies/password/complexity", PASSWORD_COMPLEXITY)
    ensure_policy(api, "OIDC (thời hạn token)", "/admin/v1/settings/oidc", OIDC_SETTINGS, key="settings")

    pid = ensure_project(api, out)
    if pid != "<dry-run>":
        ensure_role(api, pid)
        for name, cfg in APPS.items():
            ensure_app(api, pid, name, cfg, out)
        ensure_machine_user(api, out)
        ensure_roles_action(api)
        ensure_admin_grants(api, pid)

    if DRY:
        say("info", "dry-run: không ghi gì")
        return
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", "utf-8")
    say("xong", f"đã ghi {OUT_FILE.relative_to(ROOT)} (bí mật, đã .gitignore)")


if __name__ == "__main__":
    sys.exit(main())
