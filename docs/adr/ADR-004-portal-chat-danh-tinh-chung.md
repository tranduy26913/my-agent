# ADR-004: Hai web (Portal + Chat), một danh tính chung qua Zitadel

- Trạng thái: **Đề xuất** (2026-11-23). Cùng ngày sửa: phần mềm đăng nhập đổi từ Keycloak sang Zitadel sau khi đo RAM (docs/05 mục 4.1).
- Liên quan: ADR-001 (phân quyền tài liệu), ADR-003 (phân quyền dữ liệu HR), `kb-admin/src/features/kb/MERGE.md`
- Kế hoạch thực hiện: [`docs/06-ke-hoach-zitadel.md`](../06-ke-hoach-zitadel.md), [`docs/07-khung-giao-dien-portal.md`](../07-khung-giao-dien-portal.md)

## Bối cảnh

1. Hiện có hai giao diện web: LibreChat (chat) và `kb-admin` (quản trị kho tri thức). `MERGE.md` dự định gộp kb-admin vào LibreChat, nghĩa là phải **fork** LibreChat. Mỗi lần LibreChat ra bản mới sẽ phải gộp lại.
2. Ngoài chat, người dùng còn cần các công cụ có màn hình riêng, ví dụ tra cứu nghỉ phép, danh bạ, OCR. Admin cần quản lý tài khoản, nhật ký và chi phí. Những màn này không hợp nhét vào khung chat.
3. Thông tin người dùng đang nằm ở **ba** nơi:
   - tài khoản LibreChat (Mongo);
   - bảng `users` của backend, dùng JWT riêng và `role` admin/manager/staff;
   - bảng `employees`, dùng để tạo `Principal` theo email.

   Hệ quả là người dùng phải đăng nhập hai lần, và trang "tạo tài khoản" không biết phải tạo vào đâu.
4. `knowledge-mcp` đang tin header `X-User-Email` do LibreChat gửi, có kèm một token dùng chung là `X-KB-Token`. Ai có được token đó thì tự khai là ai cũng được.

## Quyết định

### 1. Hai web, không fork LibreChat
| Web | Địa chỉ | Vai trò |
|---|---|---|
| **Portal** (Next.js, phát triển tiếp từ `kb-admin`) | `portal.tranduyai.id.vn` | Dùng chung cho người dùng (`/tools/*`) và admin (`/admin/*`) |
| **Chat** (LibreChat v0.8.9, giữ nguyên) | `chat.tranduyai.id.vn` | Hội thoại với Agent; tool chạy qua MCP |

- Hai web chỉ nối với nhau bằng **liên kết**: portal có nút "Mở Trợ lý", LibreChat có `CUSTOM_FOOTER` dẫn về portal.
- `MERGE.md` mức 2 (gộp vào LibreChat) **không làm nữa**.
- Không dùng `admin-panel` có sẵn của LibreChat cho nghiệp vụ CTA. Nó chỉ quản trị LibreChat.

### 2. Một nghiệp vụ, hai cách gọi
Mỗi tool chỉ cài **một lần** ở tầng service của backend (`app/rag/*`, `app/hr/*`, ...), với cùng một bộ quy tắc ADR-001 và ADR-003. Có hai cách gọi tới nó:
- portal gọi qua REST: `FastAPI /api/*`;
- chat gọi qua MCP: `knowledge-mcp`, sau này thêm `hr-mcp`.

Nhờ vậy, một người không thể xem được trên portal mà lại bị chặn trong chat, hoặc ngược lại.

### 3. Zitadel là nơi đăng nhập duy nhất (OIDC)
- **Zitadel chỉ trả lời câu hỏi "người này là ai"**, gồm đăng nhập, mật khẩu, phiên đăng nhập và khoá tài khoản.
- **"Người này được làm gì" vẫn do backend quyết định**, dựa trên `employees.roles` tra theo `email` trong token. Không chép vai trò CTA sang Zitadel, để vai trò chỉ được định nghĩa ở một nơi.
- **Ngoại lệ duy nhất là project role `librechat-admin`** trong Zitadel. LibreChat cần nó qua `OPENID_ADMIN_ROLE`, và nó chỉ dùng để quản trị LibreChat.
- Bỏ đăng nhập bằng mật khẩu của LibreChat (`ALLOW_EMAIL_LOGIN=false`) và bỏ JWT tự phát của backend. Sau khi chuyển xong thì xoá bảng `users`.
- `knowledge-mcp` chuyển sang nhận `Authorization: Bearer {{LIBRECHAT_OPENID_ACCESS_TOKEN}}` rồi tự kiểm chữ ký. Không còn tin email do client tự khai nữa.

### 4. Admin xem nội dung tài liệu Mật trên portal: được phép, nhưng bắt buộc ghi log
- Ngoại lệ này chỉ áp dụng cho `GET /api/kb/documents/{docId}`. `acl_sql`/`can_read` và luồng chat/RAG **giữ nguyên** quy tắc "không có ngoại lệ cho admin".
- Ghi log `audit_logs.event = "kb_view_classified"` khi tài liệu có `classification = "Mat"` **và** admin tự mình không `can_read` tài liệu đó. Ghi log và đọc dữ liệu nằm trong cùng một transaction. Ghi log thất bại thì không trả chunk (fail closed).
- Lượt xem hiện trong lịch sử của tài liệu. Giao diện báo cho admin biết lượt xem này đã được ghi.

## Các phương án đã cân nhắc

| Phương án | Vì sao không chọn |
|---|---|
| Gộp portal vào LibreChat (MERGE.md mức 2) | Phải giữ một bản fork; React 18 và TanStack v4 bó buộc mô-đun |
| Tự viết OIDC provider | Rủi ro bảo mật cao, mất nhiều tuần, không mang lại giá trị nghiệp vụ |
| Keycloak | Phương án đầu tiên, vì doanh nghiệp dùng phổ biến nhất. Bị loại sau khi đo: lúc model đã nạp sẵn máy chỉ còn khoảng 2,2 GB, còn Keycloak (Java) cần 0,5–1 GB, nên kéo xuống dưới ngưỡng 1,5 GB. Hai bên đều là OIDC chuẩn, nên đổi lại về sau không phải sửa kiến trúc |
| Auth0 / Entra External ID (dịch vụ ngoài) | Danh tính nằm ngoài hệ thống, trái với hướng chạy on-prem cho dữ liệu Mật (P3) |
| Đưa vai trò CTA vào Zitadel | Hai nơi cùng định nghĩa vai trò sẽ lệch nhau; ADR-003 đã dựa trên `employees` |
| Admin không được xem chunk tài liệu Mật | Admin cần soát lỗi chunking/OCR của mọi tài liệu; ghi log đủ để truy vết |

## Hệ quả

- **Tốt:**
  - Đăng nhập một lần cho cả hai web.
  - Trang `/admin/users` chỉ cần gọi User Service (API v2) của Zitadel.
  - MCP xác thực bằng token thật thay cho email tự khai.
  - Không phải fork LibreChat.
- **Phải trả:**
  - Thêm một container. Zitadel viết bằng Go, nhẹ hơn Keycloak, nhưng vẫn phải đo bằng `docker stats` khi chạy thật. Nếu dùng giao diện đăng nhập mới (Login v2) thì có thêm container thứ hai.
  - Thêm thứ cần sao lưu: DB `zitadel` **và** `ZITADEL_MASTERKEY`. Thiếu một trong hai là mất toàn bộ tài khoản.
  - Mọi dịch vụ phụ thuộc vào `auth.tranduyai.id.vn`: Zitadel sập thì không ai đăng nhập được.
  - Zitadel không export cấu hình ra một file như realm của Keycloak, nên phải viết script khởi tạo chạy lại được nhiều lần.
- **Rủi ro cần kiểm chứng:**
  - ~~LibreChat có tự gắn tài khoản persona cũ (Mongo) vào tài khoản OIDC theo email không.~~ **Không** (đã đọc mã v0.8.9, 2026-11-23): tài khoản có `provider` khác `openid` bị từ chối đăng nhập OIDC. Các persona cũ đã bị xoá và tạo mới qua OIDC (docs/06 giai đoạn 3).
  - `{{LIBRECHAT_OPENID_ACCESS_TOKEN}}` có được truyền sang MCP qua `streamable-http` không.
  - Khi `OPENID_REUSE_TOKENS=true`, token có được làm mới đúng lúc không.

## Ca kiểm thử bắt buộc

1. Đăng nhập portal xong mở chat thì không phải đăng nhập lại, và ngược lại.
2. Token sai chữ ký, sai `iss`, sai `aud` hoặc đã hết hạn: FastAPI và knowledge-mcp đều trả 401.
3. Email trong token không có trong `employees`: trả 403 kèm lý do rõ ràng, không trả 500.
4. Nhân viên chuyển sang `da-nghi-viec`: lần gọi tiếp theo bị chặn dù token còn hạn, vì quyền tra lại từ DB ở mỗi request.
5. Khoá (deactivate) tài khoản trên Zitadel: không đăng nhập mới được; phiên hiện có hết khi token hết hạn (tối đa khoảng 15 phút).
6. Admin xem chunk của tài liệu Mật: có chunk trả về và có đúng một dòng `kb_view_classified`.
