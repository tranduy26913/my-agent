# Khung giao diện Portal

Portal là một web Next.js, phát triển tiếp từ `kb-admin/`. Nó gom **công cụ cho người dùng** và **trang quản trị cho admin** vào một chỗ. Phần chat vẫn ở LibreChat ([ADR-004](adr/ADR-004-portal-chat-danh-tinh-chung.md)). Đăng nhập dùng Zitadel ([06-ke-hoach-zitadel.md](06-ke-hoach-zitadel.md), giai đoạn 5).

Bộ mặt giữ nguyên theo `DESIGN.md`: phong cách Clean (P13), sidebar trắng, nền nội dung xám, flat, font Inter, màu nhấn chàm `#4f46e5`.

## 1. Sơ đồ trang

| Đường dẫn | Ai thấy | Nội dung | Backend | Trạng thái |
|---|---|---|---|---|
| `/` | mọi người | Trang chủ: lời chào, lối tắt tới công cụ, nút "Hỏi Trợ lý" | `GET /api/me` | **Đã làm** (dùng `getMe()` giả) |
| `/tools/tra-cuu` | mọi người | Ô hỏi đáp về quy chế, câu trả lời có trích dẫn, chọn ngày hiệu lực | `POST /api/kb/ask` (cùng service với `ask_knowledge`) | Chưa làm |
| `/tools/van-ban` | mọi người | Duyệt các văn bản **mình được xem**, có lọc theo loại/phòng/hiệu lực | `GET /api/kb/library` (đã lọc qua `acl_sql`) | Chưa làm |
| `/tools/nghi-phep` | mọi người; quản lý có thêm tab "Nhóm của tôi" | Số ngày phép còn lại, đơn nghỉ; quản lý xem đơn của cấp dưới | `/api/hr/*` (ADR-003) | Chưa làm, chờ hr service |
| `/tools/danh-ba` | mọi người | Tìm đồng nghiệp; số điện thoại hiện theo `can_view_phone` | `/api/hr/directory` | Chưa làm |
| `/tools/ocr` | mọi người (hoặc theo vai trò, xem mục 6) | Tải ảnh/PDF lên, nhận lại văn bản | **Session OCR quyết định** | Chừa chỗ |
| `/admin/kb` | `admin` | Kho tri thức: mô-đun `features/kb` đã có | `/api/kb/*` | **Đã làm**; backend `/api/kb` có sẵn, nối qua BFF (cần `API_DEV_TOKEN` để dùng dữ liệu thật) |
| `/admin/users` | `admin` | Tài khoản: tạo, khoá/mở, đặt lại mật khẩu; liên kết với `employees` | `/api/admin/users` → Zitadel User Service (API v2) | Chưa làm |
| `/admin/audit` | `admin` | Nhật ký: lọc theo người, sự kiện, thời gian; làm nổi `kb_view_classified` và `tool_denied` | `GET /api/admin/audit` | Chưa làm |
| `/admin/usage` | `admin` | Chi phí và lượt gọi theo người, theo model, theo tháng | `GET /api/admin/usage` (`usage_logs`) | Chưa làm |
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

## 4. Token màu

Hiện mọi token đều có tiền tố `kb-*`. Khung và các mô-đun mới dùng chung một bộ, nên nên đổi tiền tố thành `--p-*` (portal). Có hai cách:
- **Cách nhanh:** giữ `kb-*` cho tất cả, chấp nhận tên hơi lệch nghĩa.
- **Cách sạch:** đổi tên một lần bằng tìm và thay trong `theme.css`/`tokens.css` và các class `*-kb-*`, rồi chạy `typecheck` và `lint`.

Nên chọn cách sạch, và làm **trước** khi thêm mô-đun thứ hai.

## 5. Trạng thái mà trang nào cũng phải có

| Trạng thái | Cách hiện |
|---|---|
| Đang tải | Khung xương (skeleton) đúng hình bảng/thẻ, không dùng spinner giữa trang |
| Rỗng | Một câu nói rõ vì sao rỗng, kèm một hành động. Ví dụ: "Chưa có tài liệu nào. Nạp tài liệu" |
| Lỗi | Thông báo bằng tiếng Việt kèm nút "Thử lại"; không hiện stack trace |
| 401 | Phiên hết hạn: chuyển về trang đăng nhập, quay lại đúng trang đang xem |
| 403 | Ghi rõ lý do backend trả về, ví dụ "Chưa có trong danh bạ nhân sự" hoặc "Cần vai trò admin" |
| Đã ghi nhật ký | Với các thao tác có ghi audit (xem tài liệu Mật, tạo tài khoản): hiện một dòng nhỏ báo cho người dùng biết |

## 6. Phần OCR: phối hợp với session đang làm OCR

Phần OCR đang được làm ở một session khác, nên tài liệu này **chỉ chừa chỗ, không đặt hợp đồng API thay cho bên đó**.
- Mục `ocr` có sẵn trong `nav.ts`. Trang `/tools/ocr` tạm hiện trạng thái "Đang phát triển".
- Khi bên OCR chốt endpoint, mô-đun `features/ocr/` viết `types.ts` theo đúng hợp đồng đó. Các trạng thái chắc chắn sẽ cần: đang tải lên (có %), đang xử lý (OCR chậm, mỗi trang vài giây), kết quả theo từng trang, lỗi định dạng hoặc lỗi quá cỡ.
- Ba câu cần bên OCR trả lời trước khi làm giao diện:
  1. Xử lý đồng bộ, hay trả `jobId` rồi để portal hỏi lại trạng thái?
  2. Kết quả có được lưu không, hay chỉ trả về một lần?
  3. Có cho "đưa kết quả vào kho tri thức" không? Nếu có thì đi qua `/api/kb/documents` (có quyền và metadata), không tạo đường riêng.
- Upload trong `/admin/kb` đã có xử lý OCR phía backend (`ocr_pages`). Trang `/tools/ocr` khác ở chỗ người dùng chỉ lấy chữ ra, **không** nạp vào kho.

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

Khi Zitadel xong (giai đoạn 5 của 06), chỉ cần thay `getMe()` mock bằng phiên thật và bật `middleware.ts`.
