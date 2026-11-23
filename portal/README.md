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
- Chưa có chế độ tối nên không khai khối `.dark`.
- `src/hooks/use-mobile.ts` đã sửa sang `useSyncExternalStore` vì bản gốc của shadcn vi phạm luật `set-state-in-effect` của lint.
- Thêm component mới: `npx shadcn@latest add <ten>` trong thư mục `portal/`. Kiểm tra lại file sinh ra bằng `npm run lint`.

## Vai trò (tạm, chưa có đăng nhập)

`getMe()` (`src/lib/me.server.ts`) trả người dùng giả. Ở chế độ dev, menu người dùng có công tắc **Admin / Nhân viên** (cookie `portal-dev-role`) để thử menu theo vai trò. Build production luôn là nhân viên. Có Zitadel thì chỉ thay thân hàm `getMe()`.

## Dữ liệu Kho tri thức

Mặc định dùng **dữ liệu giả** (`features/kb/api/mock.ts`). Muốn gọi FastAPI thật, tạo `.env.local`:

```
NEXT_PUBLIC_KB_API_URL=/api/kb
API_DEV_TOKEN=<Bearer JWT của một tài khoản admin trong bảng users của backend>
```

rồi khởi động lại `npm run dev` (biến `NEXT_PUBLIC_*` được nhúng lúc khởi động). Trình duyệt chỉ gọi `/api/kb/*` cùng origin; BFF gắn token và chuyển tới `BACKEND_URL` (mặc định `http://localhost:8000`). Không đặt token thì backend trả 401.

### Trang Tra cứu (`/tools/tra-cuu`)

Dành cho mọi nhân viên, và backend lọc tài liệu theo **người đang hỏi**. BFF xưng danh bằng `PORTAL_BFF_TOKEN` (cùng giá trị trong `backend/.env` và `portal/.env.local`) kèm email người đăng nhập; backend chỉ tin email khi token đúng, rồi tra phòng ban và vai trò trong bảng `employees` (cùng cách tin cậy như knowledge-mcp). Người dùng giả ở chế độ dev là hai nhân viên có thật trong seed: `huy.do@saoviet.example` (admin) và `binh.le@saoviet.example`. Đây là cầu nối tạm đến khi có Zitadel (`get_asker_email` trong `backend/app/api/deps.py`). Cần backend, LocalAI (`LLM_PROVIDER=local`) và model embedding đang chạy; lần hỏi đầu sau khi khởi động có thể mất tới vài phút.
