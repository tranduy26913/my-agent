# portal: công cụ cho nhân viên + trang quản trị

Next.js 16 (App Router) + Tailwind 4 + TanStack Query + lucide-react. Phát triển tiếp từ `kb-admin` (đã đổi tên). Thiết kế: [docs/07](../docs/07-khung-giao-dien-portal.md), bộ mặt: [DESIGN.md](../DESIGN.md).

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
src/lib/                 Me (người dùng), getMe() giả, token backend
src/features/<ten>/      mô-đun giao diện, KHÔNG import next/* (ESLint chặn); hiện có `kb`
src/styles/              token màu --p-* (tokens.css) và ánh xạ Tailwind (theme.css)
src/host/                adapter Next cho mô-đun (router, QueryClient)
```

Thêm một trang công cụ: thêm một dòng vào `src/shell/nav.ts` + một `page.tsx` trong `src/app/(portal)/`. Sidebar, trang chủ và tiêu đề tự cập nhật.

## Vai trò (tạm, chưa có đăng nhập)

`getMe()` (`src/lib/me.server.ts`) trả người dùng giả. Ở chế độ dev, menu người dùng có công tắc **Admin / Nhân viên** (cookie `portal-dev-role`) để thử menu theo vai trò. Build production luôn là nhân viên. Có Zitadel thì chỉ thay thân hàm `getMe()`.

## Dữ liệu Kho tri thức

Mặc định dùng **dữ liệu giả** (`features/kb/api/mock.ts`). Muốn gọi FastAPI thật, tạo `.env.local`:

```
NEXT_PUBLIC_KB_API_URL=/api/kb
API_DEV_TOKEN=<Bearer JWT của một tài khoản admin trong bảng users của backend>
```

rồi khởi động lại `npm run dev` (biến `NEXT_PUBLIC_*` được nhúng lúc khởi động). Trình duyệt chỉ gọi `/api/kb/*` cùng origin; BFF gắn token và chuyển tới `BACKEND_URL` (mặc định `http://localhost:8000`). Không đặt token thì backend trả 401.
