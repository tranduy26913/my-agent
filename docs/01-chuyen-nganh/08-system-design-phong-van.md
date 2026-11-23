# Khung system design cho phỏng vấn AI Agent Engineer (GĐ5)

> Đề luyện: *"Thiết kế nền tảng AI Agent nội bộ cho tập đoàn 5.000 nhân viên, dữ liệu nhạy cảm, tích hợp Teams."* Thời lượng 45 phút. Khung dưới đây là **thứ tự nói**, nội dung bạn tự điền.

## Bước 1. Làm rõ yêu cầu (5 phút) – hỏi trước khi vẽ
- Người dùng: bao nhiêu người dùng đồng thời? Phòng ban nào dùng trước?
- Bài toán: hỏi đáp tài liệu? tra cứu dữ liệu nhân sự? tự động hóa hành động (tạo đơn, gửi mail)?
- Dữ liệu: ở đâu (SharePoint, HRM, ERP, file server)? Định dạng? Bao nhiêu? Scan nhiều không?
- Ràng buộc: dữ liệu được ra cloud không? Có Entra ID không? Ngân sách? Yêu cầu kiểm toán?
- Tiêu chí thành công: tiết kiệm bao nhiêu giờ, tỉ lệ dùng, độ chính xác?

## Bước 2. Ước lượng quy mô (3 phút)
Ví dụ: 5.000 NV × 30% dùng hằng ngày × 10 câu/ngày = 15.000 câu/ngày; giờ cao điểm ~3.000 câu/giờ ≈ 1 câu/giây. Mỗi câu trung bình 8k token vào, 600 token ra → tính chi phí/tháng theo bảng giá model đang chọn. Kho tài liệu 200.000 trang → ~1 triệu chunk → pgvector đủ.

## Bước 3. Kiến trúc tổng thể (10 phút)
Vẽ các lớp: kênh (web, Teams) → cổng (auth, rate limit) → nền tảng chat/agent → lớp tool/MCP (dữ liệu nhân sự, kho tri thức, kỹ năng, hệ thống nghiệp vụ) → dữ liệu → model gateway (cloud/on-prem, routing) → observability.

## Bước 4. Đi sâu 2–3 phần (15 phút) – chọn phần người phỏng vấn quan tâm
- **RAG**: nạp, OCR, chunk, hybrid, rerank, lọc quyền, phiên bản, eval.
- **Agent**: workflow hay agent cho từng bài toán; HITL; max steps; tool design.
- **Quyền**: danh tính từ Entra ID đi đến MCP (OBO), RBAC/ABAC, audit.
- **Skill library**: vòng đời, duyệt, chống nhiễm độc.

## Bước 5. Bảo mật (4 phút)
Phân loại dữ liệu, injection, PII, least privilege, audit, model nào cho dữ liệu nào.

## Bước 6. Chi phí và hiệu năng (3 phút)
Routing model, caching, giới hạn theo user/phòng ban, batch cho việc nền.

## Bước 7. Giám sát và chất lượng (3 phút)
Trace, golden set theo phòng ban, feedback loop, cảnh báo chi phí/lỗi.

## Bước 8. Lộ trình triển khai (2 phút)
Pilot 1 phòng ban (6–8 tuần) → đo ROI → mở rộng theo đợt → CoE quản trị. Xem `docs/04-quy-trinh-chuan-hoa-tu-dong-hoa-agent.md`.

## Lỗi hay mắc khi trả lời
- Vẽ ngay mà không hỏi yêu cầu.
- Mọi thứ đều là "agent" – không phân biệt workflow.
- Bỏ quên quyền và audit.
- Không có cách đo chất lượng.
- Không nói đánh đổi ("chọn X vì..., chấp nhận nhược điểm Y").

## Mẫu STAR (điền câu chuyện của bạn)
| | Nội dung |
|---|---|
| Situation | Bối cảnh, quy mô, ràng buộc |
| Task | Bạn chịu trách nhiệm gì |
| Action | Bạn đã làm gì (cụ thể, ngôi "tôi") |
| Result | Số liệu, bài học |

Ba câu chuyện cần chuẩn bị: tích hợp hệ thống khó; xử lý sự cố production; tự động hóa một quy trình.
