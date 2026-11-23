# kb-admin — trang quản trị kho tri thức

Next.js 16 (App Router) + Tailwind 4 + TanStack Query + lucide-react. Chạy độc lập với LibreChat.

```powershell
npm install
npm run dev        # http://localhost:3100/kb
npm run typecheck
npm run lint
```

## Cấu trúc: hai lớp tách bạch

```
src/features/kb/   MÔ-ĐUN giao diện. Không biết Next.js. Sẽ chép sang LibreChat khi gộp.
src/host/          VỎ Next.js: router, provider, khung sidebar/header. Bỏ đi khi gộp.
src/app/           Route, layout, font của Next.
```

Hàng rào ESLint cấm `src/features/kb` import `next/*`. Chi tiết và các bước gộp: [`src/features/kb/MERGE.md`](src/features/kb/MERGE.md).

## Nguồn dữ liệu

Mặc định dùng **dữ liệu giả** (`features/kb/api/mock.ts`), chạy được khi chưa có backend. Có FastAPI thật thì đặt:

```
NEXT_PUBLIC_KB_API_URL=http://localhost:8000/api/kb
NEXT_PUBLIC_CHAT_URL=http://localhost:3080      # link "Mở Trợ lý"
```

Hợp đồng endpoint backend cần làm nằm ở đầu `features/kb/api/http.ts`.
