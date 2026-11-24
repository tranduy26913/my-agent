# portal: công cụ cho nhân viên + trang quản trị

Next.js 16 (App Router) + Tailwind 4 + **shadcn/ui** (base Radix, style nova) + TanStack Query + lucide-react. Phát triển tiếp từ `kb-admin` (đã đổi tên). Thiết kế: [docs/07](../docs/07-khung-giao-dien-portal.md), bộ mặt: [DESIGN.md](../DESIGN.md).

```powershell
npm install
npm run dev        # http://localhost:3100
npm run typecheck
npm run lint
```

## Cấu trúc

```
src/app/(portal)/        trang cần đăng nhập, bọc bởi khung (sidebar + header)
src/app/(portal)/admin/  cổng admin: layout.tsx kiểm vai trò, không đủ quyền thì sang /403
src/app/api/[...path]/   BFF: gắn Bearer phía server rồi chuyển tiếp tới FastAPI (chỉ nhóm khai ở ROUTES)
src/shell/               AppShell, SidebarNav, UserMenu; nav.ts là NGUỒN DUY NHẤT của điều hướng
src/lib/                 utils.ts (cn), Me (người dùng), getMe() giả, token backend
src/components/ui/       component của shadcn (button, sheet, table, sidebar...), thêm bằng `npx shadcn@latest add <ten>`
src/features/<ten>/      mô-đun giao diện, KHÔNG import next/* (ESLint chặn); chỉ được import @/components/ui/* và @/lib/utils
src/host/                adapter Next cho mô-đun (router, QueryClient)
```

Thêm một trang công cụ: thêm một dòng vào `src/shell/nav.ts` + một `page.tsx` trong `src/app/(portal)/`. Sidebar, trang chủ và tiêu đề tự cập nhật.

## Giao diện (shadcn/ui)

- Màu theo quy ước của shadcn (`bg-background`, `bg-card`, `text-muted-foreground`, `bg-primary`, `border-input`...), giá trị khai ở khối `:root` cuối `src/app/globals.css`. Muốn đổi bộ mặt thì sửa khối đó. Trạng thái ngoài bộ chuẩn: `success`, `warning` (dùng `bg-success/10 text-success`).
- Font Inter (có subset tiếng Việt). Không dùng Geist mặc định của shadcn vì không có subset này.
- Mọi phần tử giao diện dựng từ component shadcn (Button, Input, Select, Checkbox, RadioGroup, ToggleGroup, Field, Item, Empty, Spinner, Avatar, Card, Table, Tabs, Sheet, AlertDialog, DropdownMenu, Sidebar...). Không viết lại bằng thẻ HTML thuần; cần phần tử mới thì `shadcn add` trước.
- Ô nhập (Input, Textarea, Select) không có viền: nền xám nhạt `bg-muted`, chỉ hiện vòng chàm khi focus. Đặt trên nền xám của trang thì thêm `bg-card` để ô vẫn nổi.
- Các component trong `src/components/ui/` đã được chỉnh về bộ mặt Clean cũ (nút cao 40px bo 12px, thẻ bo 16px không viền, tab phẳng, lớp phủ nhạt không mờ, hộp xoá bo 16px). Thang bo góc là mặc định của Tailwind. Khi chạy `shadcn add` hoặc cập nhật component, kiểm tra lại các tệp này bằng mắt.
- Chưa có chế độ tối nên không khai khối `.dark`, và `globals.css` khai `@custom-variant dark` để các lớp `dark:*` của shadcn không tự bật theo cài đặt tối của hệ điều hành.
- `src/hooks/use-mobile.ts` đã sửa sang `useSyncExternalStore` vì bản gốc của shadcn vi phạm luật `set-state-in-effect` của lint.
- Thêm component mới: `npx shadcn@latest add <ten>` trong thư mục `portal/`. Kiểm tra lại file sinh ra bằng `npm run lint`.

## Đăng nhập (Auth.js + Zitadel, docs/06 giai đoạn 5)

- Cấu hình ở `.env.local` (mẫu: `.env.example`): `AUTH_SECRET`, `AUTH_URL`, `AUTH_ZITADEL_ISSUER/ID/SECRET/PROJECT_ID`. Giá trị ID/secret/project lấy từ `infra/zitadel/out/generated.json`.
- `src/auth.ts`: phiên là JWT mã hoá trong cookie httpOnly; access/refresh/id token nằm TRONG cookie nên trình duyệt không đọc được. Tự làm mới access token trước khi hết hạn (kết quả làm mới được nhớ vài phút, vì Zitadel xoay refresh token và một lần tải trang gọi callback nhiều lần). Không làm mới được thì phiên bị coi là hết hạn và chuyển về `/login`.
- `src/app/api/auth/[...nextauth]/route.ts` chỉ mở bước callback OIDC; `/api/auth/session`, `/csrf`, `/signin`... trả 404 vì `/session` sẽ đưa token ra trình duyệt. Đăng nhập, đăng xuất đi bằng server action (`src/lib/auth-actions.ts`); đăng xuất gọi cả `end_session` của Zitadel.
- `src/proxy.ts` (Next 16 đổi tên middleware thành proxy): chưa có phiên thì chuyển về `/login` (riêng `/api/*` trả 401). Chỉ kiểm "có phiên không"; vai trò admin kiểm ở `app/(portal)/admin/layout.tsx` và ở FastAPI.
- `src/lib/me.server.ts`: `getMe()` gọi `GET /api/me` của backend bằng token của người dùng. Họ tên, vai trò (admin...), phòng ban lấy từ bảng `employees`, KHÔNG từ token. Đã đăng nhập Zitadel mà không có trong danh bạ, đã nghỉ việc, hoặc backend từ chối token thì sang `/no-access?reason=...` (không tự về `/login` để khỏi lặp vô hạn).
- BFF (`src/app/api/[...path]/route.ts`) gắn `Authorization: Bearer <access token của chính người đăng nhập>`; backend tự kiểm chữ ký và tra quyền theo email, nên portal không thể nói hộ quyền người khác.
- Dev khi chưa đăng nhập được: `AUTH_ZITADEL_INTERNAL_URL=http://127.0.0.1:8180` cho phép server portal gọi Zitadel qua localhost (dùng `X-Forwarded-Host`, vì `fetch` của Node bỏ header `Host`). Trình duyệt vẫn phải tới được `https://auth.tranduyai.id.vn` để nhập mật khẩu, nên vẫn cần route tunnel.

### Không còn người dùng giả

Giai đoạn 6 (docs/06) đã gỡ `PORTAL_DEV_AUTH`, `API_DEV_TOKEN` và `PORTAL_BFF_TOKEN`. Muốn xem portal phải đăng nhập Zitadel thật; để thử hai vai trò thì đăng nhập bằng một admin (vd `huy.do`) và một nhân viên thường (vd `binh.le`) ở hai cửa sổ ẩn danh.

## Trang Nhật ký và Chi phí (`/admin/audit`, `/admin/usage`)

Mô-đun `features/audit` và `features/usage` đọc `GET /api/admin/audit` và `GET /api/admin/usage` (chỉ admin). Cùng công tắc với Kho tri thức: có `NEXT_PUBLIC_KB_API_URL` thì gọi backend thật qua BFF, bỏ trống thì dùng dữ liệu giả. Backend không trả nội dung câu hỏi của nhân viên hay dữ liệu công cụ (`backend/app/admin_service.py`). Có thể chạy thêm một instance dev ở cổng khác bằng `NEXT_DIST_DIR=.next-xxx npx next dev -p 3101` để khỏi tranh khoá thư mục `.next`.

## Dữ liệu Kho tri thức

Mặc định dùng **dữ liệu giả** (`features/kb/api/mock.ts`). Muốn gọi FastAPI thật, đặt trong `.env.local`:

```
NEXT_PUBLIC_KB_API_URL=/api/kb
```

rồi khởi động lại `npm run dev` (biến `NEXT_PUBLIC_*` được nhúng lúc khởi động). Trình duyệt chỉ gọi `/api/kb/*` cùng origin; BFF gắn token của người đăng nhập và chuyển tới `BACKEND_URL` (mặc định `http://localhost:8000`). `/api/kb/*` chỉ cho nhân viên có vai trò `admin` trong bảng `employees`; `/api/kb/ask` (trang Tra cứu) cho mọi nhân viên, và backend lọc tài liệu theo phòng ban, vai trò của chính người hỏi. Cần backend, LocalAI (`LLM_PROVIDER=local`) và model embedding đang chạy; lần hỏi đầu sau khi khởi động có thể mất tới vài phút.
