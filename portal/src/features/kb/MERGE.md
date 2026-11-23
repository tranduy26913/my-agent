> **Ghi chú (2026-11-23):** kế hoạch gộp vào LibreChat đã bỏ theo ADR-004; mô-đun này chạy trong `portal/`. Token màu đã đổi từ `kb-*` thành `p-*` (tệp `src/styles/`). Giữ tài liệu này để tham khảo.

# Gộp mô-đun Kho tri thức vào LibreChat

Mô-đun này viết để **chép nguyên thư mục** `src/features/kb/` sang LibreChat, chỉ viết lại một file nhỏ ở ngoài.

## Nguyên tắc giữ cho dễ gộp

| Quy tắc | Vì sao | Ai canh |
|---|---|---|
| Không `import` gì từ `next/*`, `@/*`, hay ra ngoài thư mục `kb/` | Chép sang LibreChat là chạy, không phải gỡ Next | ESLint (`eslint.config.mjs`, thử vi phạm sẽ báo lỗi) |
| Chỉ dùng React, TanStack Query, lucide-react | LibreChat đã có cả ba | — |
| Chỉ dùng API TanStack Query có ở **cả v4 lẫn v5** | LibreChat dùng v4, kb-admin dùng v5 | Chú thích đầu `hooks.ts`; dùng `isBusy()` thay `isPending` |
| Không dùng API chỉ có ở React 19 (`use`, `ref` làm prop, `useActionState`…) | LibreChat dùng React 18 | Xem lại khi review |
| Mọi màu là token `kb-*` (`bg-p-surface`, `text-p-muted`…) | Đổi một file là ăn theo giao diện và chế độ tối của LibreChat | `theme.css` + `tokens.css` |
| Không có sidebar, header, đăng nhập trong mô-đun | Đó là khung của ứng dụng chủ | `KbAdminPage` chỉ vẽ phần nội dung |
| Mọi thứ cần từ bên ngoài đi qua `KbHost` (`host.tsx`) | Một điểm nối duy nhất | — |

`KbHost` gồm đúng hai thứ: **`api`** (lấy dữ liệu từ đâu) và **`route`** (panel nào đang mở, lưu ở đâu).

## Ba mức gộp, từ nhẹ đến sâu

1. **Mức 0, không sửa LibreChat:** giữ kb-admin chạy riêng, đặt link qua lại (`CUSTOM_FOOTER` trong `.env` của LibreChat; mục "Mở Trợ lý" đã có trong kb-admin). Dùng chung OIDC thì không phải đăng nhập lại.
2. **Mức 1, nhúng bằng iframe:** thêm một tab trỏ tới kb-admin. Vẫn phải sửa code thanh bên của LibreChat.
3. **Mức 2, gộp hẳn (tài liệu này):** chép mô-đun vào client LibreChat, thêm một route và một mục thanh bên.

Chỉ mức 2 đụng vào source LibreChat. Nó là bản fork, nên chỉ làm khi thật cần một tab liền mạch.

## Các bước mức 2

Đường dẫn dưới đây đã đối chiếu với LibreChat v0.8.9 (`librechat-src/client/`). Trang **Insights** của họ (`/insights`) có sẵn route và mục thanh bên, dùng làm mẫu.

1. **Chép thư mục.** `kb-admin/src/features/kb/` → `client/src/features/kb/`. **Xoá** `tokens.css` (màu mặc định của kb-admin, LibreChat không cần).
2. **Nối màu.** Trong `client/src/style.css` thêm:
   ```css
   @import './features/kb/theme.css';
   @source './features/kb';            /* để Tailwind quét class của mô-đun */
   :root {
     --p-bg: var(--surface-secondary);   /* đổi tên biến cho khớp tokens.css của LibreChat */
     --p-surface: var(--surface-primary);
     --p-fg: var(--text-primary);
     --p-muted: var(--text-secondary);
     /* …các --p-* còn lại, xem danh sách trong features/kb/tokens.css */
   }
   ```
   Chế độ tối của LibreChat đổi biến gốc nên mô-đun tự ăn theo.
3. **Viết adapter** `client/src/routes/KbRoute.tsx` (thay cho `src/host/KbNextHost.tsx`):
   ```tsx
   import { useMemo } from 'react';
   import { useSearchParams } from 'react-router-dom';
   import { KbAdminPage, KbHostProvider, createHttpKbApi } from '~/features/kb';

   export default function KbRoute() {
     const [params, setParams] = useSearchParams();
     const api = useMemo(() => createHttpKbApi({ baseUrl: '/api/kb', credentials: 'include' }), []);
     const panel = params.get('panel');
     const docId = params.get('doc');
     const host = useMemo(() => ({
       api,
       route: {
         panel: panel === 'upload' || (panel === 'detail' && docId) ? panel : null,
         docId,
         open: (p, id) => setParams(id ? { panel: p, doc: id } : { panel: p }),
         close: () => setParams({}),
       },
     }), [api, panel, docId, setParams]);
     return <KbHostProvider host={host}><KbAdminPage /></KbHostProvider>;
   }
   ```
   (Với TanStack Query v4 của LibreChat, không cần `Providers`: họ đã có `QueryClientProvider`.)
4. **Thêm route** trong `client/src/routes/index.tsx` (cạnh route Insights): `{ path: 'kb', element: <KbRoute /> }`.
5. **Thêm mục thanh bên** trong `client/src/hooks/Nav/useUnifiedSidebarLinks.ts` (cạnh mục Insights, icon `Library` của lucide-react).
6. **Xác thực.** `createHttpKbApi` mặc định gửi cookie. LibreChat dùng JWT: truyền ``getHeaders: () => ({ Authorization: `Bearer ${token}` })``, token lấy từ `useAuthContext()`. Phía FastAPI kiểm token đó (cùng nhà cung cấp OIDC thì dùng chung được).
7. **Gọi API thế nào.** Nếu để trình duyệt gọi thẳng FastAPI thì cấu hình CORS, hoặc cho proxy ngược của LibreChat chuyển `/api/kb` sang FastAPI.

## Việc chưa kiểm chứng

- Mô-đun **chưa được chạy trong LibreChat thật**. Hàng rào ESLint chỉ chứng minh không phụ thuộc Next, không chứng minh chạy được trên React 18 + TanStack Query v4. Lần gộp đầu tiên cần chạy thử và sửa nếu lệch.
- `tokens.css` của LibreChat (`packages/client/src/theme/tokens.css`) có tên biến riêng, danh sách ánh xạ ở bước 2 cần đối chiếu từng biến.
