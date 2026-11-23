# DESIGN.md — Portal (công cụ người dùng + quản trị)

- **Sản phẩm:** portal nội bộ gom công cụ cho nhân viên (tra cứu quy chế, văn bản, nghỉ phép, danh bạ, OCR) và trang quản trị cho admin (kho tri thức, tài khoản, nhật ký, chi phí). Chat nằm ở LibreChat (ADR-004).
- **Kiến trúc:** Next.js ở `portal/`, phát triển tiếp từ `kb-admin`. Khung ở `src/shell/` (một file `nav.ts` điều khiển menu, quyền xem, lối tắt trang chủ); mỗi mô-đun trong `src/features/<ten>/` không import `next/*`. Chi tiết: `docs/07-khung-giao-dien-portal.md`.
- **Người dùng:** nhân viên (công cụ) và admin (quản trị), làm trên máy tính, có xem được trên điện thoại.
- **Bộ mặt:** Clean (P13): sidebar trắng, nội dung trên nền xám, flat, font Inter.
- **Màu nhấn:** Chàm `#4f46e5`. Mọi màu là token `p-*` (`bg-p-surface`, `text-p-muted`...), khai ở `portal/src/styles/tokens.css`, ánh xạ sang Tailwind ở `theme.css`. Không dùng màu cứng. Chưa có dark mode.
- **Trạng thái mọi trang phải có:** đang tải (skeleton), rỗng, lỗi + thử lại, 401, 403 (nêu lý do), đã ghi nhật ký.
- **Màn đã dựng:** khung (sidebar theo vai trò, drawer điện thoại, menu người dùng), trang chủ, `/403`, trang "Đang phát triển"; `/admin/kb` (danh sách, nạp tài liệu, chi tiết).
