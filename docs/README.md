# Bộ tài liệu học tập AI Agent Engineer

Điểm bắt đầu: [00-ke-hoach-hoc-tap.md](00-ke-hoach-hoc-tap.md) – kế hoạch 3 tuần. Mọi tài liệu khác phục vụ kế hoạch này.

## 1. Tài liệu chuyên ngành – `01-chuyen-nganh/`
Tài liệu định hướng: bản chất, hiểu lầm hay gặp, câu hỏi tự kiểm, nguồn gốc để đọc tiếp. **Không thay thế** việc đọc nguồn gốc và tự viết note của bạn trong `docs/notes/`.

| File | Giai đoạn |
|---|---|
| [00-thuat-ngu.md](01-chuyen-nganh/00-thuat-ngu.md) | Tra cứu Anh–Việt mọi giai đoạn |
| [01-librechat.md](01-chuyen-nganh/01-librechat.md) | GĐ0, GĐ4 |
| [02-agent-va-tool-calling.md](01-chuyen-nganh/02-agent-va-tool-calling.md) | GĐ1 ngày 3–5, 7 |
| [03-mcp.md](01-chuyen-nganh/03-mcp.md) | GĐ1 ngày 6–7 |
| [04-rag-ocr-eval.md](01-chuyen-nganh/04-rag-ocr-eval.md) | GĐ2 |
| [05-skills-va-experience-memory.md](01-chuyen-nganh/05-skills-va-experience-memory.md) | GĐ3 ngày 12–13 |
| [06-tu-dong-hoa-va-kenh-chat.md](01-chuyen-nganh/06-tu-dong-hoa-va-kenh-chat.md) | GĐ3 ngày 14–15 |
| [07-van-hanh-bao-mat-chi-phi.md](01-chuyen-nganh/07-van-hanh-bao-mat-chi-phi.md) | GĐ4 |
| [08-system-design-phong-van.md](01-chuyen-nganh/08-system-design-phong-van.md) | GĐ5 |

## 2. Dữ liệu cho RAG và MCP – `../data/`
Công ty giả lập **Sao Việt (SVT)**: 14 văn bản có metadata phân quyền/hiệu lực/phiên bản, bản scan cho OCR, dữ liệu nhân sự CSV, golden set 35 câu. Đọc [../data/README.md](../data/README.md) trước khi nạp.

## 3. Mô phỏng công việc – `03-mo-phong-cong-viec/`
Ticket, email, kịch bản đóng vai, tư liệu mini-app. Đọc [03-mo-phong-cong-viec/README.md](03-mo-phong-cong-viec/README.md) để có lịch dùng theo ngày.

## 4. Quy trình chuẩn hóa tự động hóa với Agent
[04-quy-trinh-chuan-hoa-tu-dong-hoa-agent.md](04-quy-trinh-chuan-hoa-tu-dong-hoa-agent.md) – 9 giai đoạn (G0–G8), cổng kiểm soát, thang tự động hóa L0–L5, RACI, 15 biểu mẫu, ví dụ xuyên suốt tại SVT. Dùng cho câu hỏi phỏng vấn "làm việc với phòng ban để chọn bài toán" và cho buổi demo trước Ban Giám đốc.

## 5. Nhật ký triển khai demo
[05-nhat-ky-trien-khai-demo.md](05-nhat-ky-trien-khai-demo.md) – tiến độ đưa demo lên domain qua Cloudflare Tunnel, chạy model local (Qwen3-4B) cho chat và RAG, vấn đề còn tồn tại, cách chạy lại.

## Gợi ý dùng theo ngày

| Ngày | Đọc | Dữ liệu | Mô phỏng |
|---|---|---|---|
| 1–2 | 01-librechat | tạo user theo persona trong data/README | SVT-AI-001…004 |
| 3–5 | 02-agent | hr/employees.csv | K01 + quy trình G1–G3 |
| 6–7 | 03-mcp | hr/*.csv | K02 |
| 8–11 | 04-rag | knowledge/, scan/, eval/ | K03, K04, K05 |
| 12–15 | 05, 06 | – | K06, K11, K12 |
| 16–17 | 07 | – | K07, K08, K09 |
| 18–19 | 08 + quy trình mục 16 | – | K10 |
