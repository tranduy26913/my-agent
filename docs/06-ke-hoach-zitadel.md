# Kế hoạch dựng Zitadel và nối vào hệ thống

> Ban đầu kế hoạch chọn Keycloak, nhưng sau khi đo RAM (giai đoạn 0, [docs/05 mục 4.1](05-nhat-ky-trien-khai-demo.md))
> đã chuyển sang **Zitadel**. Kiến trúc trong [ADR-004](adr/ADR-004-portal-chat-danh-tinh-chung.md) giữ nguyên, chỉ thay phần mềm đăng nhập.

Tài liệu này chỉ nói **làm thế nào**, chia thành từng giai đoạn. Mỗi giai đoạn có một điểm kiểm tra để biết đã xong chưa.

> Ghi chú phối hợp: một session khác đang tích hợp OCR, có đụng tới `backend/app/rag/ingest.py` và các file liên quan.
> Kế hoạch này **không sửa** những file đó. Phần xác thực nằm riêng ở `app/auth/`.

## Bức tranh sau khi xong

```
                     ┌──────────── auth.tranduyai.id.vn ─────────────┐
                     │  Zitadel (instance → org "SVT" → project "svt")│  DB: agent-db / database "zitadel"
                     └───▲───────────────▲───────────────▲───────────┘
             OIDC login  │               │ OIDC login     │ JWKS (kiểm chữ ký)
                         │               │                │
chat.tranduyai.id.vn ─► LibreChat     portal.tranduyai.id.vn ─► Portal (Auth.js)
                         │                                  │ /api/* (BFF, gắn Bearer)
     MCP + Bearer token  ▼                                  ▼
                   knowledge-mcp :8100  ◄── cùng service ──► FastAPI :8000
                         └──────── email trong token → employees → Principal ────────┘
```

## Đổi từ Keycloak sang Zitadel: khác nhau ở đâu

| Keycloak | Zitadel | Ảnh hưởng tới kế hoạch |
|---|---|---|
| Realm `svt`, issuer `.../realms/svt` | Instance → Organization `SVT` → **Project** `svt`; issuer là gốc domain `https://auth.tranduyai.id.vn` | `OPENID_ISSUER` và `oidc_issuer` không có đường dẫn con |
| Client | **Application** bên trong project | Hai app `librechat` và `portal` nằm chung một project |
| Audience mapper `svt-api` | Token tự có **project ID** trong `aud` | FastAPI kiểm `aud` chứa project ID |
| Realm role, nằm trong `realm_access.roles` | **Project role**, nằm trong claim `urn:zitadel:iam:org:project:roles` (một object, không phải mảng) | Đổi cách LibreChat đọc vai trò admin |
| Access token mặc định là JWT | Access token mặc định là **opaque** | Phải chọn *Auth Token Type = JWT* cho từng app |
| Export realm ra JSON | Không có bản export tương đương | Viết script khởi tạo chạy lại được nhiều lần (giai đoạn 2.5) |
| Admin REST API + service account client | API v2 (User Service) + **machine user** có PAT | Giai đoạn 4.4 |
| Bảng admin `/admin` | Console `/ui/console` | Chặn đúng đường dẫn đó khỏi internet |

## Giai đoạn 0: Đo RAM — **đã xong** (2026-11-23)

Kết quả nằm ở docs/05 mục 4.1. Lúc model đã nạp sẵn, máy còn khoảng 2,2 GB, nên chọn Zitadel thay Keycloak.

## Giai đoạn 1: Chạy Zitadel (khoảng nửa ngày) — **chạy được 2026-11-23, còn route tunnel**

**1.1 Database.** Dùng chung container `agent-db`. Lúc khởi tạo, Zitadel dùng tài khoản admin của Postgres để **tự tạo** database `zitadel` và user `zitadel`. Lúc chạy, nó chỉ dùng user `zitadel`, vì vậy backend không đọc được bảng mật khẩu của Zitadel. Mật khẩu của user `zitadel` đặt riêng, khác mật khẩu của `agent`.

**1.2 Service trong `librechat/docker-compose.override.yml`:**
| Mục | Giá trị | Lý do |
|---|---|---|
| image | `ghcr.io/zitadel/zitadel:v4.x.y` (ghim đúng bản) | Không dùng `latest` |
| command | `start-from-init --masterkeyFromEnv --tlsMode external` | Lần đầu tự khởi tạo DB; `tlsMode external` vì Cloudflare lo HTTPS |
| `ZITADEL_MASTERKEY` | 32 ký tự ngẫu nhiên, để trong `.env` | Dùng để mã hoá dữ liệu nhạy cảm trong DB. **Mất khoá này là mất toàn bộ dữ liệu**, nên phải sao lưu cùng DB |
| `ZITADEL_EXTERNALDOMAIN=auth.tranduyai.id.vn`, `ZITADEL_EXTERNALPORT=443`, `ZITADEL_EXTERNALSECURE=true` | | `iss` trong token phải là URL công khai |
| `ZITADEL_DATABASE_POSTGRES_HOST=agent-db`, `..._PORT=5432`, `..._DATABASE=zitadel` | | |
| `ZITADEL_DATABASE_POSTGRES_USER_USERNAME/PASSWORD`, `..._USER_SSL_MODE=disable` | user `zitadel` | Dùng khi chạy |
| `ZITADEL_DATABASE_POSTGRES_ADMIN_USERNAME/PASSWORD`, `..._ADMIN_SSL_MODE=disable` | user admin của `agent-db` | Chỉ dùng lúc khởi tạo |
| `ZITADEL_FIRSTINSTANCE_ORG_NAME=SVT` | | Tạo luôn organization ngay lần đầu |
| `ZITADEL_FIRSTINSTANCE_ORG_HUMAN_USERNAME/PASSWORD` | lấy từ `.env` | Admin đầu tiên. Đăng nhập lần đầu sẽ bị buộc đổi mật khẩu |
| `ZITADEL_FIRSTINSTANCE_ORG_MACHINE_MACHINE_USERNAME=bootstrap`, `..._PATPATH=/machinekey/pat.txt` | mount một thư mục chỉ máy này đọc được | Tạo sẵn machine user và PAT cho script ở giai đoạn 2.5 |
| ports | `127.0.0.1:8180:8080` | Cổng 8080 đã có LocalAI dùng; chỉ mở cho localhost |
| healthcheck | `/app/zitadel ready` (hoặc gọi `/debug/ready`) | Để `depends_on` của LibreChat chờ đúng lúc |
| `mem_limit` | ví dụ `512m` | Chặn trần RAM; đo bằng `docker stats` rồi chỉnh |

**Đã kiểm chứng (v4.20.5, 2026-11-23):** v4 mặc định bật Login V2 (`LOGINV2_REQUIRED=true`), cần container `zitadel-login` riêng. Chọn **ở lại Login V1** bằng `ZITADEL_DEFAULTINSTANCE_FEATURES_LOGINV2_REQUIRED=false`, nên không tốn thêm container. Docs Zitadel xác nhận Login V1 vẫn được hỗ trợ ở v4. Nếu sau này cần Login V2 (một số Actions V2) thì theo "Adopt Login V2". Ngoài ra healthcheck cần `ZITADEL_TLS_ENABLED=false` (xem docs/05 mục 4.2).

**1.3 Tunnel.** Thêm route `auth.tranduyai.id.vn` trỏ tới `http://localhost:8180`. Zitadel dùng gRPC/HTTP2 cho API, nên bật `http2Origin` cho route này trong cấu hình cloudflared.
- **Chặn `/ui/console` khỏi internet**: bật Cloudflare Access riêng cho `auth.tranduyai.id.vn/ui/console*`. **Không** chặn `/ui/login`, `/oauth/*`, `/oidc/*`, `/.well-known/*`, vì đó là luồng đăng nhập của người dùng.
- Muốn quản trị thì vào `http://localhost:8180/ui/console`.

**Xong khi:**
- `https://auth.tranduyai.id.vn/.well-known/openid-configuration` trả JSON, và `issuer` là `https://auth.tranduyai.id.vn`.
- `docker stats` cho thấy mức RAM thực tế (ghi vào docs/05).
- Mở console từ internet thì bị chặn.

## Giai đoạn 2: Cấu hình organization `SVT` và project `svt` (khoảng nửa ngày) — **xong 2026-11-23, trừ bước đăng nhập qua trình duyệt (chờ route tunnel)**

**2.1 Chính sách**, đặt ở mức instance hoặc org:
- **Login policy:** tắt *Register allowed*, chỉ admin được tạo tài khoản. Tắt các nhà cung cấp đăng nhập bên ngoài (IdP).
- **Lockout policy:** khoá tài khoản sau khoảng 5 lần nhập sai mật khẩu.
- **Password complexity:** tối thiểu 10 ký tự.
- **OIDC settings:** access token 10–15 phút; refresh token idle 8 giờ.
- Nếu không có SMTP thì admin tạo user với email đã xác minh sẵn (`isVerified: true`).

**2.2 Project `svt`**
- Bật *Assert Roles on Authentication*, để vai trò được đưa vào token.
- Tạo đúng **một** project role: `librechat-admin`. Không đưa vai trò SVT vào Zitadel (ADR-004 mục 3).

**2.3 Application trong project `svt`**
| App | Loại | Redirect URI | Ghi chú |
|---|---|---|---|
| `librechat` | Web, Code + PKCE, có client secret | `https://chat.tranduyai.id.vn/oauth/openid/callback` | *Auth Token Type = JWT* |
| `portal` | Web, Code + PKCE, có client secret | `https://portal.tranduyai.id.vn/api/auth/callback/zitadel`, cùng bản `http://localhost:3100/...` cho dev (bật *Development mode* để cho phép http) | *Auth Token Type = JWT* |

Hai app nằm chung project, nên access token của cả hai đều có project ID trong `aud`. FastAPI và knowledge-mcp chỉ cần kiểm project ID đó. Không cần tạo app cho FastAPI hay knowledge-mcp: hai dịch vụ này chỉ **kiểm** token, không xin token.

**2.4 Machine user cho backend:** tạo `portal-admin-api` kiểu Machine, cấp quyền org **`ORG_USER_MANAGER`** (chỉ quản lý user, không có quyền khác), rồi tạo PAT. PAT để trong `backend/.env`. Machine user `bootstrap` tạo ở giai đoạn 1 có quyền rộng hơn, chỉ dùng cho script khởi tạo; xong việc thì vô hiệu hoá nó.

**2.5 Lưu cấu hình vào repo (thay cho việc export realm)**
- Viết script `infra/zitadel/bootstrap.py`, dùng PAT của `bootstrap`. Script tạo hoặc cập nhật các policy, project, role, hai app và machine user ở trên.
- Script phải chạy lại được nhiều lần mà kết quả không đổi: thứ gì đã có thì đối chiếu, không tạo trùng.
- Client ID và client secret mới sinh ra được ghi vào một file nằm trong `.gitignore`.
- Lựa chọn khác là dùng Terraform provider chính thức của Zitadel. Cách này đúng kiểu "infrastructure as code" hơn, nhưng phải học thêm Terraform. Với bản demo, script Python là đủ.

**2.6 Người dùng.** Script `backend/app/seed_zitadel.py` dùng chung client ở giai đoạn 4.4:
- Đọc `data/hr/employees.csv`, tạo human user theo email, đặt mật khẩu tạm và bật buộc đổi mật khẩu.
- Nhân viên `da-nghi-viec` thì tạo xong deactivate luôn.
- Chạy lại được nhiều lần mà kết quả không đổi.
- Mật khẩu tạm ghi vào file nằm trong `.gitignore`, giống `persona-accounts.txt`.

**Đã làm (2026-11-23):**
- `infra/zitadel/bootstrap.py` (2.1-2.5): đặt chính sách ở mức **instance** (chỉ có một org nên đủ), tạo project `svt` (assert roles), role `librechat-admin`, hai app `librechat` và `portal` (JWT, Code + PKCE, client secret basic, dev mode) và machine user `portal-admin-api` (chỉ `ORG_USER_MANAGER`). Chạy lại không đổi gì; có `--dry-run`. Kết quả vào `infra/zitadel/out/generated.json` (`.gitignore`). Chạy: `cd backend; .\.venv\Scripts\python ..\infra\zitadel\bootstrap.py`.
- Đã kiểm PAT của `portal-admin-api`: tạo project/app trả 403, sửa chính sách instance trả 403, quản lý user (`/v2/users`) dùng được.
- `backend/app/auth/zitadel_admin.py` (client User Service, sẽ dùng tiếp ở 4.4) và `backend/app/seed_zitadel.py` (2.6): 24 tài khoản từ `employees.csv`, email xác minh sẵn, buộc đổi mật khẩu; người `da-nghi-viec` bị khoá. Mật khẩu tạm ở `infra/zitadel/out/user-passwords.txt`. Chạy: `.\.venv\Scripts\python -m app.seed_zitadel`.
- Khác kế hoạch: đường PUT của chính sách khoá tài khoản là `/admin/v1/policies/password/lockout` (GET là `.../policies/lockout`); thêm `ignoreUnknownUsernames` và tắt passkey. Machine user `bootstrap` **chưa vô hiệu hoá** vì bootstrap.py cần nó để chạy lại; vô hiệu hoá ở giai đoạn 6.
- Kiểm bằng Session API (chưa qua trình duyệt): binh.le đúng mật khẩu tạo được phiên, sai mật khẩu bị từ chối, người nghỉ việc trả `User.NotActive`.
- **Còn lại:** đăng nhập qua `https://auth.tranduyai.id.vn/ui/login` cần route tunnel (docs/05 mục 4.2). Chưa kiểm access token JWT có sẵn claim `email` không (giai đoạn 4).

**Xong khi:** đăng nhập được một persona, ví dụ binh.le, tại `https://auth.tranduyai.id.vn/ui/login`. Chạy lại `bootstrap.py` lần nữa thì không có gì thay đổi.

## Giai đoạn 3: Nối LibreChat (khoảng 2–3 giờ) — **cấu hình xong 2026-11-23; chưa đăng nhập thử được (chờ route tunnel)**

Trong `librechat/.env`:
- `OPENID_ISSUER=https://auth.tranduyai.id.vn`, `OPENID_CLIENT_ID=<client id của app librechat>`, `OPENID_CLIENT_SECRET=...`, `OPENID_SESSION_SECRET=<chuỗi ngẫu nhiên>`.
- `OPENID_USE_PKCE=true`.
- `OPENID_SCOPE="openid profile email urn:zitadel:iam:org:project:id:<projectId>:aud"`. Scope cuối bảo đảm `aud` có project ID.
- `OPENID_ADMIN_ROLE=librechat-admin`, `OPENID_ADMIN_ROLE_PARAMETER_PATH=urn:zitadel:iam:org:project:roles`.
  - **Cần kiểm chứng:** ở Zitadel, claim này là một object dạng `{ "librechat-admin": { "<orgId>": "..." } }`, không phải mảng. Phải đọc code LibreChat xem nó kiểm vai trò bằng tên key hay bằng `includes`. Nếu không khớp thì cho Zitadel chạy một **Action** để thêm claim `roles` dạng mảng.
- `OPENID_REUSE_TOKENS=true`. Biến này bắt buộc để MCP nhận được access token thật. Đặt `OPENID_REUSE_MAX_SESSION_AGE_MS` gần bằng thời hạn access token.
- `OPENID_BUTTON_LABEL="Đăng nhập SVT"`.
- **Chỉ đặt `ALLOW_EMAIL_LOGIN=false` và `OPENID_AUTO_REDIRECT=true` khi OIDC đã chạy ổn.** Làm sớm hơn thì tự khoá mình ra ngoài.
- Sửa `.env` xong phải chạy `docker compose up -d --force-recreate --no-deps api`.

Cần kiểm chứng thêm:
- Container `api` có gọi ra được `https://auth.tranduyai.id.vn` không. Nó đi ra internet rồi quay về qua tunnel; nếu lỗi thì dùng `extra_hosts`.
- Persona cũ đăng nhập qua OIDC có gắn vào **đúng** tài khoản Mongo cũ theo email không (lịch sử chat còn nguyên).

**Đã làm (2026-11-23):**
- `librechat/.env` (đã .gitignore): toàn bộ `OPENID_*` như trên (PKCE, `REUSE_TOKENS`, scope có `...:aud`, `ADMIN_ROLE=librechat-admin`, `ADMIN_ROLE_TOKEN_KIND=id`, `ADMIN_ROLE_PARAMETER_PATH=roles`, nhãn nút "Đăng nhập SVT", `USE_END_SESSION_ENDPOINT`); `ALLOW_SOCIAL_LOGIN=true`, `ALLOW_SOCIAL_REGISTRATION=true` (tài khoản chỉ do admin tạo ở Zitadel nên an toàn). **`ALLOW_EMAIL_LOGIN` và `OPENID_AUTO_REDIRECT` chưa đổi** (làm sau khi đăng nhập OIDC chạy ổn). `librechat.yaml`: `registration.socialLogins: ['openid']`; MCP `knowledge-mcp` thêm `Authorization: Bearer {{LIBRECHAT_OPENID_ACCESS_TOKEN}}`, giữ `X-User-Email` và `X-KB-Token` làm đường tạm. Đã `up -d --force-recreate --no-deps api`; `/api/config` báo `openidLoginEnabled: true`.
- Chưa có route tunnel nên LibreChat chưa gọi được `https://auth.tranduyai.id.vn`: log báo "OpenID Connect configuration is unavailable. Retrying in 5000ms". Không chặn khởi động; LibreChat tự thử lại nền và sẽ tự đăng ký chiến lược OIDC khi route có.
- **Kiểm chứng bằng đọc mã v0.8.9 (trong container):**
  1. *Vai trò admin:* LibreChat đọc claim bằng lodash `get` rồi chỉ chấp nhận **mảng hoặc chuỗi**; claim `urn:zitadel:iam:org:project:roles` là object nên admin không bao giờ khớp. Đã xử lý bằng **Action Zitadel `addRolesClaim`** (gắn vào flow Complement Token: trước userinfo/ID token và trước access token) thêm claim `roles` là mảng role key. Role `librechat-admin` được cấp cho nhân viên có vai trò `admin` trong `employees.csv` (hiện `huy.do`, `khoa.dang`) bởi `infra/zitadel/bootstrap.py`; ai không còn là admin thì bị thu hồi khi chạy lại.
  2. *Tài khoản cũ:* `findOpenIDUser` **từ chối** (AUTH_FAILED) người dùng có `provider` khác `openid`; 5 persona đều là `local` nên không gắn được theo email. Đã chọn **xoá 5 persona** (binh.le, ha.pham, mai.ngo, duc.hoang, huy.do) bằng script chính thức `delete-user` (dừng container api trước, vì script đòi xác nhận không còn tiến trình LibreChat nào khác); họ sẽ được tạo mới ở lần đăng nhập OIDC đầu tiên. Mất 5 hội thoại và 18 tin nhắn cũ. Bản sao lưu toàn bộ DB Mongo trước khi xoá: `librechat/backups/LibreChat-2026-11-23-before-personas.archive.gz` (đã .gitignore, khôi phục bằng `mongorestore --gzip --archive=...`). Tài khoản `tranduyai...@gmail.com` (local, ADMIN) giữ nguyên nên là đường vào dự phòng khi đã tắt đăng nhập mật khẩu của người khác. Lưu ý: tắt `ALLOW_EMAIL_LOGIN` sẽ khoá luôn tài khoản này; cân nhắc trước khi tắt.
  3. *Token cho MCP:* chuỗi `Authorization: Bearer {{LIBRECHAT_OPENID_ACCESS_TOKEN}}` đúng định dạng LibreChat yêu cầu. Người dùng không đăng nhập OIDC thì biến không được thay; knowledge-mcp coi header chứa `{{` hoặc rỗng như không có Bearer rồi dùng đường `X-KB-Token` (đã có test).
- **Chưa kiểm được** (cần đăng nhập thật): nút "Đăng nhập SVT" chạy trọn; `iss`/`aud` của token LibreChat nhận; user mới được tạo; `huy.do` được nâng thành ADMIN; token đến knowledge-mcp và `ask_knowledge` chạy bằng Bearer; container `api` gọi được `https://auth.tranduyai.id.vn` (nếu lỗi thì thêm `extra_hosts`).
- Sau khi đăng nhập OIDC chạy ổn: `KB_MCP_ALLOW_SHARED_TOKEN=false` ở backend, bỏ hai header cũ trong `librechat.yaml`, rồi cân nhắc `ALLOW_EMAIL_LOGIN=false` và `OPENID_AUTO_REDIRECT=true`.

**Xong khi:** binh.le đăng nhập chat qua Zitadel và vẫn thấy lịch sử hội thoại cũ; user được gán `librechat-admin` thấy menu quản trị của LibreChat.

## Giai đoạn 4: Backend kiểm token (khoảng nửa ngày) — **xong phần code và test 2026-11-23; chưa thử với token thật (chờ route tunnel)**

**4.1 Mô-đun mới `backend/app/auth/oidc.py`** (không đụng `security.py` cho tới khi chuyển xong):
- Dùng `jwt.PyJWKClient(jwks_uri)` có sẵn trong `pyjwt` để lấy khoá. Cache khoá; gặp `kid` lạ thì tải lại đúng một lần.
- Kiểm: `algorithms=["RS256"]`, `issuer`, **`aud` chứa project ID**, `exp`/`nbf`, và `email_verified` phải là `true`.
- **Cần kiểm chứng:** access token JWT của Zitadel có sẵn claim `email` không. Nếu không có thì chọn một trong hai:
  - bật *User Info inside ID Token* / *assertion* cho app; hoặc
  - gọi `userinfo` một lần rồi cache theo `sub`.
- Một dependency `get_principal()`: token → `email` → `load_principal(db, email)`.
  - Không tìm thấy nhân viên: trả 403 "Chưa có trong danh bạ nhân sự".
  - `active=False`: trả 403.
- `require_role("admin")` kiểm trên `Principal.roles` (dữ liệu từ `employees`), không kiểm trên token.
- Thêm vào `config.py`: `oidc_issuer`, `oidc_project_id`. `jwks_uri` lấy từ discovery.

**4.2 Dùng trong `/api/kb`.** Bước 5 của kế hoạch `/api/kb` đổi từ `get_current_user` sang `get_principal`. Bỏ phần CORS, vì portal đã proxy.

**4.3 `knowledge_mcp`.** Trong `librechat.yaml`, header của MCP server đổi thành `Authorization: "Bearer {{LIBRECHAT_OPENID_ACCESS_TOKEN}}"`. `_authenticate()` kiểm token bằng chính hàm ở 4.1. Trong thời gian chuyển, giữ `X-KB-Token` làm phương án dự phòng sau một cờ cấu hình, chuyển xong thì xoá.

**4.4 Client cho User Service** (chuẩn bị cho `/admin/users`). Tạo `app/auth/zitadel_admin.py`:
- Gọi API v2 bằng `httpx`, gắn `Authorization: Bearer <PAT của portal-admin-api>`.
- Các hàm: tạo human user, tìm user theo email, deactivate/reactivate, đặt mật khẩu tạm có buộc đổi.
- Mỗi lần gọi đều ghi `audit_logs`, ví dụ `event="user_create"`, kèm người thực hiện.

**4.5 Test.** Tạo cặp khoá RSA ngay trong test và tự ký token, như vậy không cần Zitadel đang chạy. Phủ ca kiểm thử 2–4 của ADR-004. Thêm một ca: token có `aud` là project khác thì phải bị từ chối.

**Đã làm (2026-11-23):**
- `backend/app/auth/oidc.py`: `KeyStore` (cache JWKS, kid lạ chỉ tải lại tối đa mỗi 30 giây), `OidcVerifier` (chỉ RS256; kiểm `iss`, `aud` chứa project id, `exp`, `nbf`; email phải đã xác minh), `get_principal`, `require_role`. Quyền lấy từ `employees.roles`, tra lại ở mỗi request; chưa có trong danh bạ hoặc đã nghỉ việc thì 403. Chưa cấu hình OIDC thì mọi Bearer bị 401 (fail closed).
- **Email:** nếu token không có claim `email` thì hỏi `userinfo` của Zitadel rồi cache 5 phút theo `sub` (cũng làm lộ token bị thu hồi hoặc tài khoản bị khoá, tối đa sau 5 phút). Chưa biết token thật có sẵn email không; kiểm khi có luồng đăng nhập thật.
- **Chạy song song với đường cũ** (xoá ở giai đoạn 6), qua `app/api/deps.py`: `get_kb_admin` nhận JWT HS256 cũ (role admin) hoặc token Zitadel của nhân viên có vai trò `admin`; `get_asker_email` ưu tiên Bearer, còn header cầu nối `X-Portal-Token` khi không có Bearer. Có Bearer mà sai thì từ chối, không lùi về đường cũ.
- **Audit của người dùng Zitadel:** họ chưa có dòng trong bảng `users` nên `audit_logs.user_id = NULL` và email ghi vào `detail.actor` (lịch sử tài liệu hiện email đó). Không nhét `employee_id` vào `user_id`, vì hai không gian id sẽ lẫn nhau. Cột "người nạp" (`uploaded_by`) của tài liệu do admin Zitadel nạp sẽ để trống đến giai đoạn 6 (đổi cột sang lưu email, cần migration).
- `knowledge_mcp.authenticate_headers`: nhận `Authorization: Bearer`; không có Bearer thì dùng `X-KB-Token` + `X-User-Email` khi cờ `KB_MCP_ALLOW_SHARED_TOKEN=true` (mặc định). Header chứa ký tự ngoài ASCII giờ bị từ chối thay vì lỗi 500.
- Cấu hình: `OIDC_ISSUER`, `OIDC_PROJECT_ID`, `OIDC_INTERNAL_URL`, `OIDC_HOST_HEADER` (đã đặt trong `backend/.env` cho dev; phải restart FastAPI và knowledge-mcp mới nhận).
- Test (tests/test_oidc.py, tests/oidc_testkit.py, token tự ký bằng khoá RSA sinh trong test): sai chữ ký/iss/aud, hết hạn, thiếu exp, `nbf`, alg none, HS256, kid lạ; xoay khoá; vai trò trong token bị bỏ qua; email không có trong danh bạ (403, không 500); nhân viên nghỉ việc bị chặn dù token còn hạn; admin xem tài liệu Mật vẫn ghi `kb_view_classified` kèm email. Backend 368 test đạt.
- Ghi `audit_logs` cho client `zitadel_admin` (4.4): **đã làm 2026-11-24** cùng trang `/admin/users` ([docs/07 mục 9.1](07-khung-giao-dien-portal.md)); client mở rộng thêm `list_humans`, `get_user`, `set_temp_password`; cần `ZITADEL_ADMIN_PAT` trong `backend/.env`.
- **Kiểm với Zitadel thật:** đã xác nhận verifier tải được JWKS thật qua `OIDC_INTERNAL_URL`. Chưa có access token của người dùng thật (cần luồng đăng nhập qua trình duyệt, chờ route tunnel), nên chưa kiểm `aud` có chứa project id và claim `email` trong token thật.

**Xong khi:**
- `pytest` chạy đạt.
- `curl` với token thật của binh.le gọi `/api/kb/documents` trả 403, vì binh.le không phải admin.
- Cùng lệnh đó với token của admin trả 200.

## Giai đoạn 5: Portal đăng nhập (khoảng nửa ngày) — **xong phần code 2026-11-23; chưa chạy trọn luồng với Zitadel thật (chờ route tunnel)**

Chi tiết giao diện nằm ở [`07-khung-giao-dien-portal.md`](07-khung-giao-dien-portal.md). Riêng phần xác thực:
- **Auth.js (next-auth v5)** dùng provider Zitadel (hoặc provider OIDC chung). Phiên đăng nhập lưu trong cookie httpOnly của portal, trình duyệt **không bao giờ cầm access token**. Scope gồm cả `urn:zitadel:iam:org:project:id:<projectId>:aud` và `offline_access` để có refresh token.
- **Theo mô hình BFF (Backend For Frontend):** route handler `src/app/api/[...path]/route.ts` đọc phiên, gắn `Authorization: Bearer` rồi chuyển tiếp tới FastAPI `:8000`. Không dùng `rewrites`, vì `rewrites` không gắn header được.
- Làm mới token trong callback `jwt` của Auth.js khi token sắp hết hạn. Làm mới thất bại thì đưa người dùng về trang đăng nhập.
- Đăng xuất phải gọi cả `end_session_endpoint` của Zitadel. Nếu không, bấm đăng nhập lại sẽ vào luôn mà không hỏi mật khẩu.
- `middleware.ts` chặn mọi route trừ `/api/auth/*`. Menu `/admin/*` hiện theo `GET /api/me`.

**Đã làm (2026-11-23)** (chi tiết: [portal/README.md](../portal/README.md)):
- Backend: `GET /api/me` (`app/api/me.py`) trả họ tên, phòng ban, vai trò từ bảng `employees` theo email trong token; chỉ nhận token Zitadel. 5 test, backend 373 test đạt.
- Portal: `src/auth.ts` (Auth.js v5, provider Zitadel, PKCE + state, JWT phiên mã hoá trong cookie httpOnly, tự làm mới token, nhớ kết quả làm mới vì Zitadel xoay refresh token), `src/proxy.ts` (Next 16), trang `/login` và `/no-access`, đăng xuất gọi `end_session` của Zitadel, `getMe()` gọi `/api/me`, BFF gắn Bearer của chính người dùng. Route `/api/auth/*` chỉ mở bước callback (đóng `/session` vì nó đưa token ra trình duyệt).
- Đã kiểm với Zitadel THẬT (qua localhost) và cookie phiên giả: chưa đăng nhập thì `/` về `/login` và `/api/*` trả 401; `/api/auth/session|csrf|signin` trả 404; bấm "Đăng nhập SVT" tạo đúng URL authorize (client, redirect_uri, scope có `...:aud`, PKCE S256, state); phiên hợp lệ nhưng backend không trả `/api/me` thì sang `/no-access`; phiên hết hạn có refresh token hỏng bị Zitadel từ chối rồi về `/login?error=session`; `callbackUrl=//evil.example` bị đưa về `/`.
- **Chưa kiểm được** (cần đăng nhập thật qua trình duyệt, tức route tunnel `auth.tranduyai.id.vn`): bước callback đổi code lấy token; làm mới token thành công; `aud` của access token có chứa project id không; token có claim `email` không (nếu không, backend hỏi `userinfo`); đăng xuất qua `end_session`; `post_logout_redirect_uri` đã khai ở Zitadel (`http://localhost:3100`, `https://portal.tranduyai.id.vn`). Tôi không tạo user thăm dò để lấy token thật: hệ thống chặn việc tạo tài khoản mang email của nhân viên thật.
- Còn lại của giai đoạn này: chưa có test tự động cho portal (chưa có hạ tầng test).
- Dev: `AUTH_ZITADEL_INTERNAL_URL` cho server portal gọi Zitadel qua localhost; `PORTAL_DEV_AUTH=1` giữ lại người dùng giả để làm giao diện (xoá ở giai đoạn 6 cùng `API_DEV_TOKEN`, `PORTAL_BFF_TOKEN`).

**Xong khi:** ca kiểm thử 1 của ADR-004 đạt (đăng nhập một lần, dùng được cả hai web).

### Kết quả kiểm thật (2026-11-24, sau khi có route `auth.` và CNAME)

- Route: `https://auth.tranduyai.id.vn/.well-known/openid-configuration` trả 200, issuer đúng. Router nhà giữ cache DNS "không tồn tại" nên đã đổi DNS máy sang 1.1.1.1/8.8.8.8 (cả IPv6).
- Portal: admin đăng nhập qua `/login` → Zitadel → callback; `GET /api/me` trả 200. Nghĩa là `aud` = project id, email đã xác minh, và chữ ký RS256 đều khớp giả định (backend chấp nhận cả khi claim `email` thiếu, nhờ userinfo).
- LibreChat: container gọi được `auth.tranduyai.id.vn` (không cần `extra_hosts`); đăng nhập OIDC tạo user mới và gán ADMIN theo role `librechat-admin`.
- **Đăng xuất `end_session` (kiểm 2026-11-24, sửa 1 lỗi):** lần đầu Zitadel trả `post_logout_redirect_uri invalid`, vì portal gửi `.../login` trong khi danh sách khai ở Zitadel chỉ có gốc URL; Zitadel so khớp **chính xác**. Đã đổi sang gốc URL (`auth-actions.ts`), gốc URL tự chuyển về `/login` vì phiên đã xoá. Sau khi sửa đăng xuất chạy đúng.
- **binh.le (nhân viên thường):** vào được portal, đúng thiết kế: `/no-access` chỉ dành cho người đăng nhập Zitadel nhưng không có trong `employees` hoặc đã nghỉ việc. `/admin/kb` bị chuyển sang `/403?need=admin`.
- **`ask_knowledge` qua Bearer:** đặt `KB_MCP_ALLOW_SHARED_TOKEN=false` rồi hỏi lại bằng binh.le, vẫn trả lời có trích dẫn (audit `rag_ask`, user_id = employees.id 15). Log knowledge-mcp có `GET /oauth/v2/keys` và `GET /oidc/v1/userinfo`: Bearer thật đã được kiểm chữ ký, và **access token không có sẵn claim `email`** nên backend hỏi `userinfo` (đúng phương án dự phòng ở 4.1).
- **Lỗi chất lượng thấy khi kiểm:** qwen3-4b từng tự điền `as_of=2023-10-05` khi gọi `ask_knowledge` dù docstring bảo bỏ trống, nên lọc hết tài liệu và trả "không tìm thấy" (audit 2063). Lần sau nó không điền. Cần chặn ở phía server (mục 5 danh sách việc).
- **Chưa kiểm:** `/api/kb/documents` trả 403 trực tiếp với binh.le; làm mới token (access token 15 phút).
- Lỗi thấy khi dùng LibreChat: `ResumableAgentController ... no_user_key` (endpoint đang đòi khoá do người dùng tự nhập; không liên quan OIDC).

## Giai đoạn 6: Dọn dẹp

- **OCR đã xong phần này (2026-11-24):** `/api/ocr/*` dùng token Zitadel (`get_ocr_user`), ghi `employees.id`; `ocr_jobs.user_id` không có khoá ngoại nên không cần migration. Còn lại là phần `/api/kb` (`uploaded_by`).
**Kế hoạch làm (2026-11-24).** Hiện trạng DB thật: `users` chỉ có dòng `portal-dev`, `conversations` rỗng, cả 14 tài liệu có `uploaded_by` NULL, nên migration rất nhẹ. Route `/auth/login` đã không còn trong code. Thứ tự:
1. Backend: bỏ `get_legacy_user`, JWT HS256, `require_roles`, bcrypt (`security.py` chỉ còn `UserInfo`); bỏ model `User`, `Conversation`, `Message` (chưa dùng ở đâu); `Actor` chỉ còn email; `uploaded_by` đổi sang **email** (varchar), người nạp hiện thẳng trên trang tài liệu; `get_asker_email` chỉ nhận Bearer; knowledge-mcp chỉ nhận Bearer; xoá `jwt_secret`, `kb_mcp_token`, `kb_mcp_allow_shared_token`, `portal_bff_token`.
2. Test: đổi `get_legacy_user` thành `get_kb_admin`, bỏ `add_user`, xoá ca "đường cũ".
3. Portal và LibreChat: bỏ `X-Portal-Token`, `PORTAL_BFF_TOKEN`, `API_DEV_TOKEN`, `PORTAL_DEV_AUTH`; bỏ `X-KB-Token` và `X-User-Email` ở `librechat.yaml`.
4. DB thật: `backend/app/migrate_stage6.py` (mặc định chỉ in việc sẽ làm, `--apply` mới chạy): đổi kiểu cột `uploaded_by`, rồi xoá `messages`, `conversations`, `users`. **Chỉ chạy sau khi có bản dump và được cho phép rõ ràng.**
5. Sau cùng: vô hiệu hoá machine user `bootstrap`, cân nhắc `ALLOW_EMAIL_LOGIN=false` và `OPENID_AUTO_REDIRECT=true`, cập nhật docs/05.

**Đã làm (2026-11-24):**
- Backend: `security.py` chỉ còn `UserInfo`; `deps.py` chỉ nhận Bearer Zitadel (`get_kb_admin`, `get_asker_email`, `get_ocr_user`); xoá `get_legacy_user`, `get_current_user`, `create_access_token`, `require_roles`, bcrypt, model `User`. `Actor` chỉ còn `email`; `documents.uploaded_by` là email (varchar 255), audit của thao tác quản trị ghi `user_id = NULL` và email vào `detail.actor`. `conversations.user_id` không còn khoá ngoại (nay là employees.id). Xoá `jwt_secret`, `jwt_expire_minutes`, `kb_mcp_token`, `kb_mcp_allow_shared_token`, `portal_bff_token` khỏi `config.py` và `.env.example`.
- knowledge-mcp chỉ nhận Bearer (cả header `{{...}}` chưa thay biến hay thiếu token đều bị từ chối). Thêm `usable_as_of`: bỏ `as_of` do mô hình tự điền khi câu hỏi không nhắc năm/ngày/tháng tương ứng.
- Portal: xoá `PORTAL_DEV_AUTH`, `NEXT_PUBLIC_PORTAL_DEV_AUTH`, `API_DEV_TOKEN`, `PORTAL_BFF_TOKEN`, `lib/backend-token.server.ts`, `lib/dev-role.ts`, công tắc vai trò ở menu người dùng. LibreChat: `librechat.yaml` bỏ `X-User-Email` và `X-KB-Token`; `KB_MCP_TOKEN` bỏ khỏi `librechat/.env` và `backend/.env`; đã `up -d --force-recreate --no-deps api`.
- DB thật: `python -m app.migrate_stage6 --apply` (bước A, sau bản dump `librechat/backups/agent-2026-11-24-before-stage6.sql`) gỡ khoá ngoại `documents_uploaded_by_fkey`, `conversations_user_id_fkey` và đổi `uploaded_by` sang varchar (cả 14 tài liệu đều NULL nên không mất dữ liệu). **Bảng `users` còn nguyên** (bước B `--drop-users` chờ bạn cho phép: nó chỉ chứa dòng `portal-dev`).
- Backend 419 test đạt, portal typecheck/lint sạch. Các dòng audit cũ của kb_*/llm_call mang id bảng `users` nên trang Nhật ký hiện "hệ thống" và trang Chi phí hiện "Người dùng #id".
- **Còn lại của giai đoạn 6:** bước B `--drop-users`; vô hiệu hoá machine user `bootstrap`; cân nhắc `ALLOW_EMAIL_LOGIN=false` và `OPENID_AUTO_REDIRECT=true` (tài khoản gmail ADMIN local sẽ bị khoá); `KB_MCP_ALLOW_SHARED_TOKEN` không còn tồn tại nên bỏ khỏi checklist.

- (Bản gốc) Xoá route `/auth/login`, bảng `users` và `create_access_token` khỏi backend. Chú ý `uploaded_by` đang là khoá ngoại tới `users.id`, cần đổi sang lưu `employee_id` hoặc email (phải có migration).
- Xoá `X-KB-Token` và `KB_MCP_TOKEN`. Vô hiệu hoá machine user `bootstrap`.
- Cập nhật `05-nhat-ky-trien-khai-demo.md`:
  - kiến trúc mới;
  - cách chạy lại sau khi khởi động máy: Zitadel phải chạy trước LibreChat;
  - cách sao lưu: DB `zitadel` **cùng với** `ZITADEL_MASTERKEY`.

## Rủi ro và cách xử lý

| Rủi ro | Dấu hiệu | Cách xử lý |
|---|---|---|
| Sai `issuer` | LibreChat báo "issuer mismatch", FastAPI trả 401 hàng loạt | Kiểm `ZITADEL_EXTERNALDOMAIN/PORT/SECURE` và `--tlsMode external` |
| Access token là opaque | FastAPI không decode được token (không phải JWT) | Đặt *Auth Token Type = JWT* cho app |
| LibreChat không nhận ra admin | Không ai thấy menu quản trị | Claim vai trò là object; dùng Action để thêm `roles` dạng mảng |
| Mất `ZITADEL_MASTERKEY` | Zitadel không khởi động, hoặc không giải mã được dữ liệu | Sao lưu khoá cùng DB, để ngoài repo |
| Tự khoá mình ra ngoài | Không đăng nhập được LibreChat | Chỉ tắt `ALLOW_EMAIL_LOGIN` sau khi giai đoạn 3 đạt |
| MCP không nhận được token | `ask_knowledge` trả 401 | Kiểm `OPENID_REUSE_TOKENS`; tạm bật lại cờ dự phòng `X-KB-Token` |
| Zitadel khởi động sau LibreChat | LibreChat lỗi discovery lúc khởi động | `depends_on` kèm healthcheck; `OPENID_DISCOVERY_RETRY_ATTEMPTS` |
| Login v2 tốn thêm RAM | Có thêm container `zitadel-login` | Dùng giao diện đăng nhập cũ, hoặc đo lại RAM (giai đoạn 1.2) |

## Thứ tự và phụ thuộc

`1 → 2 → 3`, sau đó `4` và `5` làm song song được, `6` làm cuối cùng.
Kế hoạch `/api/kb` (bước 1–4) **không phụ thuộc** vào kế hoạch này, có thể làm trước bằng JWT cũ.
