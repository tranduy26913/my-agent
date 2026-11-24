# Khung giao diện Portal

Portal là một web Next.js, phát triển tiếp từ `kb-admin/`. Nó gom **công cụ cho người dùng** và **trang quản trị cho admin** vào một chỗ. Phần chat vẫn ở LibreChat ([ADR-004](adr/ADR-004-portal-chat-danh-tinh-chung.md)). Đăng nhập dùng Zitadel ([06-ke-hoach-zitadel.md](06-ke-hoach-zitadel.md), giai đoạn 5).

Bộ mặt giữ nguyên theo `DESIGN.md`: phong cách Clean (P13), sidebar trắng, nền nội dung xám, flat, font Inter, màu nhấn chàm `#4f46e5`.

## 1. Sơ đồ trang

| Đường dẫn | Ai thấy | Nội dung | Backend | Trạng thái |
|---|---|---|---|---|
| `/` | mọi người | Trang chủ: lời chào, lối tắt tới công cụ, nút "Hỏi Trợ lý" | `GET /api/me` | **Đã làm** (dùng `getMe()` giả) |
| `/tools/tra-cuu` | mọi người | Ô hỏi đáp về quy chế, câu trả lời có trích dẫn, chọn ngày hiệu lực | `POST /api/kb/ask` (cùng hàm `ask` với `ask_knowledge`) | **Đã làm** (mô-đun `features/lookup`, backend `app/api/ask.py`) |
| `/tools/van-ban` | mọi người | Duyệt các văn bản **mình được xem**, có lọc theo loại/phòng/hiệu lực | `GET /api/kb/library` (đã lọc qua `acl_sql`) | Chưa làm |
| `/tools/nghi-phep` | mọi người; quản lý có thêm tab "Nhóm của tôi" | Số ngày phép còn lại, đơn nghỉ; quản lý xem đơn của cấp dưới | `/api/hr/*` (ADR-003) | Chưa làm, chờ hr service |
| `/tools/danh-ba` | mọi người | Tìm đồng nghiệp; số điện thoại hiện theo `can_view_phone` | `/api/hr/directory` | Chưa làm |
| `/tools/ocr` | mọi người | Tải ảnh/PDF lên, nhận lại văn bản (đồng bộ hoặc job nền) | `/api/ocr/recognize`, `/api/ocr/jobs` (ADR-005) | Đang làm (mục 6) |
| `/admin/kb` | `admin` | Kho tri thức: mô-đun `features/kb` đã có | `/api/kb/*` | **Đã làm**; backend `/api/kb` có sẵn, nối qua BFF (cần `API_DEV_TOKEN` để dùng dữ liệu thật) |
| `/admin/users` | `admin` | Tài khoản: tạo, khoá/mở, đặt lại mật khẩu; liên kết với `employees` | `/api/admin/users` → Zitadel User Service (API v2) | Chưa làm |
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
- **Chưa làm:** `/extract` (trích xuất phiếu công tác phí: đồng bộ 7–13 giây, ADR-005 mục 8); chọn engine (chỉ dùng engine mặc định).

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
