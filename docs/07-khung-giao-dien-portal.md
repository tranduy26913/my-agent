# Khung giao diện Portal

Portal là một web Next.js, phát triển tiếp từ `kb-admin/`. Nó gom **công cụ cho người dùng** và **trang quản trị cho admin** vào một chỗ. Phần chat vẫn ở LibreChat ([ADR-004](adr/ADR-004-portal-chat-danh-tinh-chung.md)). Đăng nhập dùng Zitadel ([06-ke-hoach-zitadel.md](06-ke-hoach-zitadel.md), giai đoạn 5).

Bộ mặt giữ nguyên theo `DESIGN.md`: phong cách Clean (P13), sidebar trắng, nền nội dung xám, flat, font Inter, màu nhấn chàm `#4f46e5`.

## 1. Sơ đồ trang

| Đường dẫn | Ai thấy | Nội dung | Backend | Trạng thái |
|---|---|---|---|---|
| `/` | mọi người | Trang chủ: lời chào, lối tắt tới công cụ, nút "Hỏi Trợ lý" | `GET /api/me` | **Đã làm** (dùng `getMe()` giả) |
| `/tools/tra-cuu` | mọi người | Ô hỏi đáp về quy chế, câu trả lời có trích dẫn, chọn ngày hiệu lực | `POST /api/kb/ask` (cùng hàm `ask` với `ask_knowledge`) | **Đã làm** (mô-đun `features/lookup`, backend `app/api/ask.py`) |
| `/tools/van-ban` | mọi người | Duyệt các văn bản **mình được xem**, có lọc theo loại/phòng/hiệu lực | `GET /api/kb/library` (đã lọc qua `acl_sql`) | **Đã làm** (2026-11-24, mục 9.2) |
| `/tools/nghi-phep` | mọi người; quản lý có thêm tab "Nhóm của tôi" | Số ngày phép còn lại, đơn nghỉ; quản lý xem đơn của cấp dưới | `/api/hr/leave/*` (ADR-003) | **Đã làm** (2026-11-24, mục 9.3) |
| `/tools/danh-ba` | mọi người | Tìm đồng nghiệp; số điện thoại hiện theo `can_view_phone` | `/api/hr/directory` | **Đã làm** (2026-11-24, mục 9.3) |
| `/tools/ocr` | mọi người | Tải ảnh/PDF lên, nhận lại văn bản (đồng bộ hoặc job nền) | `/api/ocr/recognize`, `/api/ocr/jobs` (ADR-005) | **Đã làm**, gồm `/extract` (mục 6, 9.4) |
| `/admin/kb` | `admin` | Kho tri thức: mô-đun `features/kb` đã có | `/api/kb/*` | **Đã làm**; backend `/api/kb` có sẵn, nối qua BFF (cần `API_DEV_TOKEN` để dùng dữ liệu thật) |
| `/admin/users` | `admin` | Tài khoản: tạo, khoá/mở, đặt lại mật khẩu; liên kết với `employees` | `/api/admin/users` → Zitadel User Service (API v2) | **Đã làm** (2026-11-24, mục 9.1) |
| `/admin/audit` | `admin` | Nhật ký: lọc theo người, sự kiện, thời gian; làm nổi `kb_view_classified` và `tool_denied` | `GET /api/admin/audit` | **Đã làm** (2026-11-23): `features/audit`, `backend/app/api/admin.py`; bộ lọc theo sự kiện, người, ngày; phân trang bằng con trỏ. **Không trả nội dung nhạy cảm** (câu hỏi của nhân viên, tham số/kết quả tool): `detail` lọc theo danh sách trắng từng sự kiện |
| `/admin/usage` | `admin` | Chi phí và lượt gọi theo người, theo model, theo tháng | `GET /api/admin/usage` (`usage_logs`) | **Đã làm** (2026-11-23): `features/usage`; chọn tháng, số tổng, bảng theo người (so với ngân sách) / mô hình / mục đích / ngày |
| `/403`, `/not-found` | | Trang báo lỗi, nói rõ lý do và cách xử lý | | **Đã làm** |

Nên làm theo thứ tự: khung + `/` → `/admin/kb` (gắn API thật) → `/admin/users` → `/tools/tra-cuu` → các trang còn lại.

## 2. Khung (shell)

```
┌────────────┬──────────────────────────────────────────────┐
│ [logo] SVT │  Tiêu đề trang                 [tên ▾]       │  ← header: tên người dùng, đăng xuất
│            ├──────────────────────────────────────────────┤
│ Trang chủ  │                                              │
│ CÔNG CỤ    │                                              │
│  Tra cứu   │            nội dung trang                    │
│  Văn bản   │                                              │
│  Nghỉ phép │                                              │
│  Danh bạ   │                                              │
│  OCR       │                                              │
│ QUẢN TRỊ   │  ← cả nhóm này chỉ hiện khi có vai trò admin │
│  Kho TT    │                                              │
│  Tài khoản │                                              │
│  Nhật ký   │                                              │
│  Chi phí   │                                              │
│ ────────── │                                              │
│ Mở Trợ lý ↗│  ← mở chat.tranduyai.id.vn                   │
└────────────┴──────────────────────────────────────────────┘
```

- **Một file cấu hình điều hướng duy nhất**, `src/shell/nav.ts`. Mỗi mục có dạng `{ href, label, icon, group: "tools" | "admin", roles?: string[] }`. Sidebar, trang chủ (lối tắt) và `middleware.ts` (chặn route) đều đọc từ file này, để không có chuyện menu một nơi, kiểm quyền một nơi rồi lệch nhau.
- **Việc ẩn menu chỉ để giao diện gọn, không phải để bảo mật.** Gõ thẳng URL `/admin/*` mà không có quyền thì bị chuyển sang `/403`, và API phía sau vẫn tự kiểm quyền.
- **Điện thoại:** `AppShell` hiện **không có menu ở màn hình nhỏ**, vì sidebar bị `hidden lg:flex`. Cần thêm nút mở drawer ở header. Đây là thiếu sót có sẵn, phải sửa khi dựng khung.
- **Chế độ tối:** chưa làm, giữ đúng `DESIGN.md`. Mọi màu vẫn đi qua token, nên thêm sau sẽ không phải sửa từng trang.

## 3. Cấu trúc thư mục

```
portal/                              (đổi tên từ kb-admin/, xem mục 7)
  src/
    app/                             route của Next: chỉ ghép layout + gọi page của mô-đun
      (portal)/layout.tsx            khung: Providers + AppShell, yêu cầu đã đăng nhập
      (portal)/page.tsx              /
      (portal)/tools/<ten>/page.tsx
      (portal)/admin/<ten>/page.tsx
      403/page.tsx
      api/auth/[...nextauth]/route.ts   Auth.js
      api/[...path]/route.ts            BFF: gắn Bearer, chuyển tiếp tới FastAPI
    shell/                           AppShell, nav.ts, UserMenu, MobileNav
    lib/auth.ts                      cấu hình Auth.js, đọc phiên đăng nhập, getMe()
    features/
      kb/                            đã có, giữ nguyên
      users/  audit/  usage/         quản trị
      lookup/  library/  leave/  directory/  ocr/   công cụ
```

**Mỗi mô-đun trong `features/<ten>/` theo khuôn của `features/kb`**, vì khuôn này đã chạy được:
- `types.ts`: kiểu dữ liệu cùng interface `XxxApi`, đây chính là hợp đồng với backend.
- `api/mock.ts` và `api/http.ts`: hai bản cài của hợp đồng. Mock giúp làm giao diện khi backend chưa có.
- `hooks.ts`: TanStack Query.
- `components/`: chỉ dùng token màu, không dùng màu cứng.
- `index.ts`: chỉ xuất ra trang chính và kiểu dữ liệu.

Hàng rào ESLint "mô-đun không import `next/*`" **nên giữ**. Lý do không còn là để gộp vào LibreChat, mà để logic giao diện không dính vào router và dễ test.

**Gọi API:** mọi mô-đun gọi đường dẫn tương đối `/api/...` tới BFF của portal. Không còn `NEXT_PUBLIC_KB_API_URL` trỏ thẳng tới FastAPI. Trình duyệt không cầm token, nên `getHeaders` của `createHttpKbApi` không cần dùng nữa; chỉ cần `credentials: "same-origin"`.

## 4. Thành phần và token màu — **đã chuyển sang shadcn/ui (2026-11-23)**

Portal dùng shadcn/ui (base Radix, style nova): component nằm ở `src/components/ui/`, thêm bằng `npx shadcn@latest add <ten>`. Token màu theo quy ước của shadcn (`background`, `card`, `primary`, `muted-foreground`, `input`...), giá trị là bộ mặt Clean ở khối `:root` của `src/app/globals.css`; trạng thái ngoài bộ chuẩn là `success` và `warning`. Tiền tố `p-*` và thư mục `src/styles/` đã bỏ.

Hàng rào ESLint đổi theo: mô-đun trong `src/features/` vẫn không import `next/*`, và chỉ được import `@/components/ui/*` cùng `@/lib/utils` từ ngoài mô-đun.

## 5. Trạng thái mà trang nào cũng phải có

| Trạng thái | Cách hiện |
|---|---|
| Đang tải | Khung xương (skeleton) đúng hình bảng/thẻ, không dùng spinner giữa trang |
| Rỗng | Một câu nói rõ vì sao rỗng, kèm một hành động. Ví dụ: "Chưa có tài liệu nào. Nạp tài liệu" |
| Lỗi | Thông báo bằng tiếng Việt kèm nút "Thử lại"; không hiện stack trace |
| 401 | Phiên hết hạn: chuyển về trang đăng nhập, quay lại đúng trang đang xem |
| 403 | Ghi rõ lý do backend trả về, ví dụ "Chưa có trong danh bạ nhân sự" hoặc "Cần vai trò admin" |
| Đã ghi nhật ký | Với các thao tác có ghi audit (xem tài liệu Mật, tạo tài khoản): hiện một dòng nhỏ báo cho người dùng biết |

## 6. Phần OCR (đã có API, ADR-005)

Backend OCR (`/api/ocr/*`) đã chốt hợp đồng. Ba câu hỏi cũ được trả lời như sau:
1. **Đồng bộ hay job:** có cả hai. `/recognize` đồng bộ cho file nhỏ (≤ 20 MB, ≤ 10 trang); `/jobs` bất đồng bộ cho file lớn (≤ 50 MB, ≤ 100 trang), portal hỏi lại trạng thái bằng `GET /jobs/{id}` (chưa có SSE).
2. **Có lưu kết quả không:** chỉ job được lưu (văn bản kết quả, không lưu file gốc, không lưu tên file), hết hạn sau 7 ngày, chỉ chủ job xem được. `/recognize` trả một lần, không lưu.
3. **Đưa vào kho tri thức:** không. Trang `/tools/ocr` chỉ lấy chữ ra. Muốn nạp kho thì dùng `/admin/kb` (đi qua phạm vi truy cập và làm sạch prompt injection).

**Đã làm (2026-11-24):** `features/ocr/` + trang `/tools/ocr`, gọi qua BFF bằng Bearer của chính người dùng (OCR đã chuyển sang Zitadel, ADR-005 mục 5).
- **Quy tắc chọn đường:** ảnh (PNG, JPEG, TIFF, BMP) là một trang nên gọi `/recognize` đồng bộ (≤ 20 MB); PDF gọi `/jobs` (≤ 50 MB) vì portal không biết số trang và OCR mỗi trang mất vài giây. Mỗi người tối đa 3 job đang chạy (429 khi vượt).
- Hiện kết quả theo từng trang kèm nhãn nguồn `text-layer` hoặc `ocr`, nút sao chép từng trang và cả tài liệu.
- Danh sách job gần đây (7 ngày) với tiến độ `pages_done/pages_total`, mở lại kết quả, xoá job.
- **Đã làm sau đó (2026-11-24):** tab "Phiếu công tác phí" gọi `/extract` (mục 9.4). **Chưa làm:** chọn engine (chỉ dùng engine mặc định).

## 7. Đổi tên `kb-admin` thành `portal`

- Đổi tên thư mục, `name` trong `package.json`, cấu hình `kb-admin` trong `.claude/launch.json`, và các đường dẫn trong `README.md`, `DESIGN.md`, `05-nhat-ky-trien-khai-demo.md`.
- Route `/kb` hiện tại chuyển thành `/admin/kb`. Có thể giữ redirect `/kb` → `/admin/kb` trong một thời gian.
- **Chỉ đổi tên khi session OCR không còn sửa gì trong `kb-admin/`.** Nếu không, hai bên sẽ sửa cùng một file ở hai đường dẫn khác nhau.
- `MERGE.md` ghi chú là đã bỏ, theo ADR-004.

## 8. Bước dựng khung đầu tiên — **đã xong (2026-11-23)**

Ghi chú khi làm: không đổi tên thẳng được `kb-admin` vì một tiến trình giữ handle thư mục `src`; đã sao chép sang `portal/` rồi xoá bản cũ (nội dung trước đó đã nằm trong git). Token đổi `kb-*` → `p-*`, CSS chung chuyển sang `src/styles/`. BFF `/api/[...path]` thay cho `rewrites` tạm của docs/08.

1. Đổi tên thư mục và đổi tiền tố token (mục 4 và 7).
2. Viết `nav.ts`, `AppShell` dùng `nav.ts` (kèm drawer cho điện thoại), và `UserMenu`.
3. Viết route group `(portal)`, chuyển `/kb` sang `/admin/kb`, và các trang tạm "Đang phát triển" cho mọi mục khác.
4. Tạm dùng `getMe()` dạng mock, có công tắc đổi vai trò admin/nhân viên ở chế độ dev, để thử menu theo vai trò khi chưa có Zitadel.
5. Chạy `npm run typecheck`, `npm run lint`, rồi mở portal ở cỡ điện thoại và cỡ máy tính, với cả hai vai trò, để kiểm.

Đã làm ở giai đoạn 5 của 06 (2026-11-23): `getMe()` đọc phiên Auth.js rồi gọi `GET /api/me`, `src/proxy.ts` (tên mới của middleware ở Next 16) chặn route; xem [portal/README.md](../portal/README.md). Người dùng giả đã gỡ ở giai đoạn 6.

## 9. Kế hoạch làm các trang còn thiếu (2026-11-24)

Thứ tự: `/admin/users` → `/tools/van-ban` → `/tools/nghi-phep` + `/tools/danh-ba` → `/extract` trong trang OCR. Mỗi mục làm backend (kèm test) trước, giao diện sau.

**Quy ước chung**
- Mô-đun giao diện mới (`features/users`, `library`, `leave`, `directory`) **chỉ có `api/http.ts`, không có `api/mock.ts`**: portal bắt buộc đăng nhập Zitadel và backend đã có, nên dữ liệu giả không còn giúp được gì, còn mỗi bản mock là thêm một nơi để lệch hợp đồng. Các mô-đun cũ giữ mock như hiện tại.
- BFF (`src/app/api/[...path]/route.ts`) thêm đúng các đường dẫn mới, dòng cụ thể đứng trước dòng chung: `kb/library` (mọi người) trước `kb` (admin); `admin/users` (admin); `hr` (mọi người, backend tự lọc phạm vi).
- Mọi thao tác ghi của admin ghi `audit_logs` với `user_id = NULL` và email người làm trong `detail.actor` (cùng quy ước với `kb_*`). Nhãn và danh sách trắng `detail` của sự kiện mới khai ở `admin_service.EVENTS`.
- Test backend: token Zitadel giả (`tests/oidc_testkit.py`), DB thật chỉ qua transaction rollback (`tests/kb_testkit.py`). Bảng mới được tạo **trong** transaction đó (DDL của Postgres rollback được), nên test không để lại gì trong agent-db và chạy được cả khi chưa migrate.

### 9.1 `/admin/users`

Nguồn sự thật về "ai là nhân viên" là bảng `employees`; Zitadel chỉ giữ tài khoản đăng nhập. Trang ghép hai bên theo email.

| Method | Đường dẫn | Việc | Audit |
|---|---|---|---|
| GET | `/api/admin/users` | Mọi nhân viên + trạng thái tài khoản Zitadel (`active`, `inactive`, `none`); thêm các tài khoản Zitadel không có trong `employees` (`employee = null`) kèm cảnh báo | không |
| POST | `/api/admin/users` `{email}` | Tạo tài khoản cho một nhân viên **đang làm** (tên lấy từ `employees`); trả mật khẩu tạm **một lần duy nhất** | `user_create` |
| POST | `/api/admin/users/{id}/deactivate` | Khoá | `user_deactivate` |
| POST | `/api/admin/users/{id}/reactivate` | Mở khoá | `user_reactivate` |
| POST | `/api/admin/users/{id}/password` | Đặt mật khẩu tạm mới (buộc đổi ở lần đăng nhập sau); trả một lần | `user_password_reset` (đặt thêm ngoài ba sự kiện được giao, vì đây cũng là thao tác ghi) |

Quyết định thiết kế:
- **Chỉ tạo tài khoản cho email có trong `employees` và đang làm.** Nếu không, một tài khoản Zitadel vô chủ đăng nhập xong vẫn bị `/no-access`; chặn từ đầu cho rõ lý do.
- **`{id}` phải là số** (id của Zitadel) rồi mới ghép vào đường dẫn gọi Zitadel; và chỉ chấp nhận user kiểu *human*. Nhờ vậy endpoint không thể dùng để khoá machine user `portal-admin-api` (tự cắt tay chân) hay `bootstrap`.
- **Không tự khoá mình**: khoá tài khoản trùng email người đang gọi thì 409.
- **Ghi audit trước khi gọi Zitadel** (flush chưa commit): DB hỏng thì từ chối trước khi làm thay đổi bên ngoài; Zitadel lỗi thì rollback nên không có dòng audit cho việc chưa xảy ra. Mật khẩu tạm **không bao giờ** vào audit, log hay `detail`; phản hồi gắn `Cache-Control: no-store`.
- Lỗi Zitadel trả 502 với câu chung ("Zitadel không thực hiện được"), chi tiết chỉ vào log. Chưa cấu hình PAT thì 503.
- Cấu hình mới: `ZITADEL_ADMIN_PAT` (PAT của `portal-admin-api`, `backend/.env`), `ZITADEL_ADMIN_URL` (rỗng = dùng `OIDC_INTERNAL_URL`, rồi `OIDC_ISSUER`); header Host dùng `OIDC_HOST_HEADER`.
- Giao diện: bảng (tên, phòng ban, vai trò, trạng thái tài khoản), ô lọc, nút theo hàng (Tạo / Khoá / Mở khoá / Đặt lại mật khẩu) qua `AlertDialog`; mật khẩu tạm hiện một lần trong hộp thoại có nút sao chép; dòng chú thích "thao tác này được ghi vào Nhật ký".
- Giới hạn đã biết: khoá tài khoản Zitadel không đổi `employees.status` (nghỉ việc do HRM quyết định) và ngược lại; trang cảnh báo khi hai bên lệch nhau (đã nghỉ việc mà tài khoản còn mở).

### 9.2 `/tools/van-ban`

`GET /api/kb/library?type=&department=&status=&q=` cho **mọi nhân viên đang làm** (`get_principal`), lọc quyền xem bằng `acl_sql(principal)` trong SQL, loại tài liệu bị cách ly.
- Trả metadata, **không trả nội dung chunk, `source`, người nạp hay danh sách phòng/vai trò được xem** (cấu hình phân quyền không phải việc của người đọc). Kèm `facets` (loại, phòng ban, đếm theo trạng thái) tính trên tập đã qua ACL, để ô lọc không lộ tài liệu người xem không được thấy.
- `status` suy ra từ ngày hiệu lực so với hôm nay, cùng quy tắc `in_force_sql` của bộ truy xuất: `hieu-luc`, `het-hieu-luc`, `chua-hieu-luc`.
- Tài liệu Mật vẫn hiện (như `withheld` của `/api/kb/ask`: người có quyền biết nó tồn tại) kèm nhãn Mật; không có nội dung nào ra khỏi endpoint này nên không cần ghi `kb_view_classified`.
- Chưa làm: xem nội dung văn bản (cần quyết định riêng về audit cho tài liệu Mật).

### 9.3 `/tools/nghi-phep`, `/tools/danh-ba`: dựng `/api/hr/*` (ADR-003)

Chưa có hr service; dữ liệu mới chỉ nằm trong `data/hr/*.csv` và `employees.leave_balance` chưa được nạp. Làm:
- **Bảng mới** (không sửa bảng `employees` đang chạy, để backend hiện tại không gãy trước khi migrate): `leave_balances`, `leave_requests`, `employee_contacts` (số điện thoại tách riêng, vì là dữ liệu bị che theo người xem). `seed_hr.py` nạp thêm ba bảng từ CSV (`init_db()` chỉ tạo bảng còn thiếu). Không viết `migrate_hr.py` riêng như dự kiến lúc đầu: chỉ thêm bảng mới, không đổi bảng cũ nên không cần; thay vào đó `python -m app.seed_hr --dry-run` chỉ đọc CSV và in việc sẽ làm. **Chưa chạy trên agent-db thật khi chưa được cho phép.**
- `authz.py`: thêm `directory_sql()` (bản SQL của `can_view_employee`, viết độc lập) và tham số `include_own` cho `scope_sql()`; test so chéo hai bản cài trên toàn bộ nhân viên (ADR-003 mục 9).
- Endpoint (cùng một cổng `get_principal`; danh tính từ token, không nhận mã nhân viên từ client):

| Method | Đường dẫn | Việc |
|---|---|---|
| GET | `/api/hr/leave/me` | Số dư phép và đơn nghỉ của chính mình (`own`) |
| GET | `/api/hr/leave/team` | Số dư và đơn của người dưới quyền theo các phạm vi `team`/`dept`/`all` mà vai trò có; không có phạm vi nào ngoài `own` thì 403 |
| GET | `/api/hr/directory?q=&department=` | Danh bạ; `phone` là `null` khi `can_view_phone` từ chối; người đã nghỉ chỉ hiện với `directory:read:inactive` |

- Audit (ADR-003 mục 8): `hr_view` khi xem dữ liệu **của người khác** (phạm vi, số dòng; không ghi nội dung), `hr_denied` khi bị từ chối.
- Lương nằm ngoài phạm vi (ADR-002/003 mục 5).
- Giao diện: `/tools/nghi-phep` có thẻ số dư + bảng đơn của mình; tab "Nhóm của tôi" chỉ hiện khi vai trò có phạm vi ngoài `own` (backend vẫn là nơi quyết định). `/tools/danh-ba` có ô tìm, lọc phòng ban, số điện thoại bị che hiện "Chỉ người cùng phòng xem được".

### 9.4 `/extract` trong trang OCR

Backend đã có (`POST /api/ocr/extract`, ADR-005 mục 8; BFF đã mở `ocr`). Chỉ làm giao diện: trang `/tools/ocr` thêm tab "Phiếu công tác phí" cạnh tab "Đọc chữ".
- Gửi một ảnh hoặc PDF (≤ 20 MB, đồng bộ, 7–13 giây), hiện: bảng khoản chi, các phát hiện (`error` / `warning` / `info`) kèm điều khoản và số tiền vượt, cờ `needs_review`.
- **Chỉ hiện kết luận "cần người xem", không có nút duyệt chi** (đúng nguyên tắc của ADR-005: hệ thống không bao giờ duyệt chi). Nói rõ model chỉ chép chữ, mọi kiểm tra là mã tất định.
- Không lưu kết quả (như `/recognize`).

### 9.5 Kiểm tra giao diện

Sau mỗi thay đổi giao diện: `npm run typecheck`, `npm run lint`, mở bằng trình duyệt ở cỡ máy tính và điện thoại, thử bằng admin và nhân viên thường. Ghi kết quả ở mục "Đã làm" từng phần khi xong.

### 9.6 Đã làm (2026-11-24) và chỗ khác kế hoạch

**Backend** (43 test mới; cả bộ đạt: 462 trước khi session STT thêm test của nó, 494 sau đó; chạy `cd backend; .venv\Scripts\python -m pytest`):
- `/api/admin/users`: `app/api/admin_users.py` + `app/user_admin_service.py`; client Zitadel mở rộng (`list_humans`, `get_user`, `set_temp_password`, `get_zitadel_admin`). Test `tests/test_admin_users.py` dùng Zitadel giả (`httpx.MockTransport`) và token Zitadel giả: kiểm quyền, ghép danh sách, tạo/khoá/mở/đặt lại mật khẩu, audit không chứa mật khẩu, thao tác bị từ chối không gọi ghi, id lạ và machine user bị 404, Zitadel lỗi thì 502 và không có dòng audit.
- `GET /api/kb/library`: `app/api/library.py` + `app/rag/library_service.py`; `tests/test_library_api.py` (ACL, không rò cấu hình phân quyền, mã văn bản thay thế chỉ hiện nếu xem được, trạng thái hiệu lực theo ngày, facet chỉ tính trên tập được xem). Phép quét cấu trúc ở `tests/test_kb_authz.py` buộc mọi route dưới `/api/kb` đòi admin: `GET /api/kb/library` được thêm vào danh sách miễn **tường minh** (cùng chỗ với `/ask`).
- `/api/hr/leave/me|team`, `/api/hr/directory`: `app/api/hr.py` + `app/hr/service.py`, bảng mới `leave_balances`, `leave_requests`, `employee_contacts` (`models.py`), `scope_sql`/`directory_sql`/`scopes_of` (`authz.py`), `seed_hr.py` nạp thêm ba bảng. `tests/test_hr_api.py`: các ca T1–T14 của ADR-003 qua API, so chéo `directory_sql` với `can_view_employee` và che số điện thoại với `can_view_phone` trên mọi vai trò, chốt chặn thứ hai (dòng mà `can()` từ chối bị bỏ), audit `hr_view`/`hr_denied`, nạp CSV thật và chạy lại không nhân đôi. Test tạo bảng mới trong transaction rollback nên agent-db thật không bị thay đổi.
- Lỗi thật bắt được nhờ test: `scope_sql` dùng `Employee` gốc, ghép với bí danh của `employees` trong truy vấn đơn nghỉ gây tích Descartes; đã sửa bằng truy vấn con.
- Sự kiện audit mới `hr_view`, `hr_denied` (nhãn và danh sách trắng ở `admin_service.EVENTS`; các sự kiện `user_*` đã có sẵn từ trước).

**Giao diện** (typecheck, lint sạch): `features/users|library|leave|directory`, tab `ExtractPanel` trong `features/ocr`, `src/lib/http.ts` (`apiJson`, `postJson`, `errorMessage`; mô-đun được import vì không dính Next), `src/host/HrNextHost.tsx`, `LibraryNextHost.tsx`, `UsersNextHost` trong `AdminNextHost.tsx`; BFF thêm `kb/library`, `hr`, `admin/users`.
- Mật khẩu tạm hiện trong hộp thoại chỉ đóng được bằng nút (không đóng khi bấm ra ngoài hay Esc) để khỏi mất.
- Tab "Nhóm của tôi" chỉ gọi API khi người dùng mở tab, vì mỗi lần gọi ghi một dòng Nhật ký.
- Khoá tạm (`USER_STATE_LOCKED`, do chính sách khoá khi nhập sai) chỉ hiển thị, chưa có thao tác mở: API tương ứng chưa được kiểm chứng.
- Tab "Phiếu công tác phí" không có nút duyệt chi; kết luận là "Cần người kiểm tra" hoặc "Chưa phát hiện điểm cần xem".

**Kiểm bằng trình duyệt** (máy tính và điện thoại 375 px, admin `huy.do` và nhân viên `binh.le`) trong môi trường cô lập, không đụng tài khoản Zitadel hay agent-db thật: IdP giả + Zitadel giả (một script tạm), Postgres tạm nạp từ `data/hr` và `data/knowledge`, backend cổng 8010, portal cổng 3101 với cookie phiên giả. Đã xác nhận:
- Admin tạo tài khoản và thấy dòng "Tạo tài khoản" trong Nhật ký (không có mật khẩu).
- Nhân viên không thấy nhóm Quản trị; `/admin/users` chuyển sang `/403`; các API admin trả 403; `/api/hr/leave/team` trả 403 "Bạn không có quyền xem phép của người khác".
- Bình thấy đúng 7,5 ngày phép (ADR-003 T1); số điện thoại ngoài phòng bị che; gõ "nguyen" ra "Nguyễn"; không tràn ngang ở cỡ điện thoại.
- Sửa trong lúc kiểm: số đếm "(0)" nháy lúc tải, tab "Chờ duyệt (0)" mặc định sang "Tất cả", bảng tổng của phiếu bị cắt ở điện thoại, nhãn trạng thái bị cắt chữ.

**Chưa kiểm:**
- `/extract` với OCR và model thật: bản kiểm chạy backend với LLM giả nên chỉ xem được phần hiển thị kết quả bằng dữ liệu giả.
- `POST /v2/users/{id}/password` của Zitadel thật: list và get đã đối chiếu với phản hồi thật (chỉ đọc); đặt mật khẩu chưa gọi thử vì sẽ đổi mật khẩu tài khoản thật.
- Đăng nhập Zitadel thật với bản mới (bản kiểm dùng cookie phiên giả).

**Việc còn lại cần bạn cho phép:** chạy `python -m app.seed_hr` trên agent-db thật (tạo ba bảng mới và nạp phép, đơn nghỉ, số điện thoại); đặt `ZITADEL_ADMIN_PAT` trong `backend/.env`; khởi động lại FastAPI cổng 8000 (bản đang chạy là bản cũ, chưa có các route mới).
