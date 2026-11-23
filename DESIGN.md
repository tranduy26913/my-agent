# DESIGN.md — Trang quản trị kho tri thức

- **Sản phẩm:** trang quản trị kho tri thức RAG (nạp, theo dõi xử lý, quyền xem, hiệu lực văn bản).
- **Kiến trúc:** Next.js riêng ở `kb-admin/`, độc lập với LibreChat nhưng viết để gộp được: mô-đun giao diện `src/features/kb/` không biết Next, vỏ Next nằm ở `src/host/` (xem `kb-admin/src/features/kb/MERGE.md`).
- **Người dùng:** người quản lý tài liệu từng phòng ban và admin, làm trên máy tính.
- **Việc chính:** nạp và gắn đúng thông tin; phát hiện tài liệu lỗi, bị cách ly; sửa quyền, thay bản mới.
- **Bộ mặt:** Clean (P13): sidebar trắng, nội dung trên nền xám, flat, font Inter.
- **Màu nhấn:** Chàm `#4f46e5`, khai ở `kb-admin/src/features/kb/tokens.css` (`--kb-primary`). Sắc: Neutral. Không có dark mode riêng (khi gộp, ăn theo LibreChat).
- **Token:** mọi màu trong mô-đun là `kb-*`, không dùng tên chung như `surface`, `muted`.
- **Màn đã dựng:** Danh sách tài liệu (tab trạng thái, tìm, chọn nhiều, gỡ hàng loạt); panel Nạp tài liệu; panel Chi tiết (Thông tin / Các đoạn / Lịch sử, kiểm tra quyền đọc, cách ly, gỡ).
