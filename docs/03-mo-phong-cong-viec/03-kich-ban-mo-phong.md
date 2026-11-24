# Kịch bản mô phỏng công việc

> Mỗi kịch bản là một "ngày làm việc thật" thu nhỏ: có người, có áp lực thời gian, có thông tin thiếu. Làm theo thứ tự: **đọc tình huống → tự xử lý trong timebox → viết đầu ra → so với "thế nào là tốt"**. Có thể nhờ AI đóng vai các nhân vật (dán phần "Vai diễn" vào làm system prompt).

| Mã | Tên | Gắn với | Timebox |
|---|---|---|---|
| K01 | Buổi khảo sát với phòng HCNS | Ngày 3–6, quy trình chuẩn hóa GĐ1–2 | 60 phút |
| K02 | Review bảo mật với kỹ sư hệ thống | Ngày 6 | 45 phút |
| K03 | Người dùng báo trả lời sai | Ngày 9–11 | 60 phút |
| K04 | Kiểm tra phiếu công tác phí | Ngày 10 | 90 phút |
| K05 | Tài liệu chứa chỉ dẫn lạ | Ngày 11 | 60 phút |
| K06 | Trình bày cơ chế kỹ năng tổ chức | Ngày 12–13 | 45 phút |
| K07 | Sự cố: câu trả lời bị cắt | Ngày 16 | 60 phút |
| K08 | Sự cố: chi phí gấp 3 | Ngày 17 | 60 phút |
| K09 | Nâng cấp LibreChat thất bại | Ngày 16 | 60 phút |
| K10 | Demo cho Ban Giám đốc | Ngày 18–19 | 30 phút |
| K11 | So sánh hợp đồng gấp (mini-app) | Ngày 14 | 45 phút |
| K12 | Biên bản họp (mini-app) | Ngày 14 | 45 phút |

---

## K01 – Buổi khảo sát với phòng HCNS
**Tình huống:** Sau email E01, chị Lan cho bạn 45 phút với chị và bạn Hà (C&B).
**Vai diễn (cho AI đóng vai):** "Bạn là Nguyễn Thị Lan, Trưởng phòng HCNS 10 năm kinh nghiệm, không rành công nghệ, lo sợ lộ dữ liệu lương, hay nói chung chung ('nhiều lắm em ạ'), chỉ đưa số liệu cụ thể khi được hỏi đúng câu. Bạn Hà biết chi tiết thao tác hằng ngày."
**Nhiệm vụ:**
1. Chuẩn bị 10 câu hỏi khảo sát (dùng Mẫu M2 trong `docs/04-...`).
2. Phỏng vấn, ghi lại quy trình hiện tại "trả lời câu hỏi nghỉ phép" dạng SIPOC + các bước.
3. Chấm điểm cơ hội tự động hóa theo ma trận ưu tiên (Mẫu M3).
**Đầu ra:** 1 trang Process Canvas + đề xuất phạm vi pilot.
**Thế nào là tốt:** có số liệu (khối lượng/tháng, phút/câu, tỉ lệ sai); tách được câu hỏi *quy chế* (RAG) và câu hỏi *số liệu cá nhân* (tool hr-mcp); xác định ngoại lệ (phép tồn chuyển năm, nhân viên thử việc, tạm ứng phép); xác định ai là chủ sở hữu nội dung; không hứa "AI trả lời được mọi thứ".

## K02 – Review bảo mật với kỹ sư hệ thống
**Tình huống:** Email E03. Khoa sẽ không mở firewall nếu chưa yên tâm.
**Vai diễn:** "Bạn là Đặng Văn Khoa, kỹ sư hệ thống 8 năm, hoài nghi AI, hỏi dồn dập và yêu cầu bằng chứng (log, demo), không chấp nhận câu 'model sẽ không làm vậy'."
**Nhiệm vụ:** trả lời 4 câu hỏi, demo thí nghiệm giả mạo email trong tham số tool (ngày 6), trình bày mô hình mối đe dọa 1 trang.
**Thế nào là tốt:** kiểm soát đặt ở code, không ở prompt; thừa nhận rủi ro còn lại; có kế hoạch nâng cấp (OBO token); tài khoản DB read-only; log không chứa giá trị lương.

## K03 – Người dùng báo trả lời sai
**Tình huống:** Email E07 (phép tồn 31/3 vs 30/6).
**Nhiệm vụ:**
1. Tái hiện bằng persona `phuong.ho@`.
2. Debug theo 5 tầng (xem `01-chuyen-nganh/04-rag-ocr-eval.md` mục 8), ghi lại tầng hỏng.
3. Sửa, thêm câu hỏi vào golden set, chạy lại eval toàn bộ để chắc không hỏng chỗ khác.
4. Trả lời người dùng theo khung B7.
**Thế nào là tốt:** chỉ ra đúng nguyên nhân (thiếu lọc `het_hieu_luc` hoặc chunk của bản cũ xếp cao hơn); có số liệu eval trước/sau; người dùng nhận được phản hồi trong ngày.

## K04 – Kiểm tra phiếu công tác phí
**Tình huống:** Email E04 và ticket CTA-AI-023.
**Nhiệm vụ:** thiết kế và làm luồng: OCR → trích xuất JSON → kiểm tra quy tắc (code, không phải LLM) → báo cáo cho kế toán.
**Câu hỏi thiết kế cần trả lời:** phần nào là LLM, phần nào là code tất định? Vì sao quy tắc định mức nên viết bằng code? Khi nào chuyển người duyệt?
**Thế nào là tốt:** phát hiện đủ 4 vấn đề của phiếu NV018, 0 cảnh báo sai cho phiếu NV017; các con số dẫn chiếu đúng Điều của Quy định 08/2025/QĐ-CTA; có `do_tin_cay` và ngưỡng chuyển người duyệt.

## K05 – Tài liệu chứa chỉ dẫn lạ (SEC-025)
**Tình huống:** Sáng thứ Hai, Bình gửi ảnh chụp: Trợ lý trả lời câu hỏi Tết Dương lịch và cuối câu có đường link `hr-update.example/verify`.
**Nhiệm vụ:** (1) khoanh vùng: tài liệu nào, ai nạp, khi nào; (2) xử lý tạm: gỡ tài liệu khỏi chỉ mục; (3) báo sự cố theo Chính sách CS-007 Điều 8 trong 1 giờ; (4) phòng thủ nhiều lớp; (5) đưa Q32, Q33 vào eval hồi quy; (6) postmortem.
**Thế nào là tốt:** không chỉ "sửa prompt"; có lớp quét lúc nạp, lớp phân định dữ liệu, lớp kiểm tra đầu ra (URL không có trong nguồn), lớp quyền (agent hỏi đáp không có tool gửi email); kiểm tra xem có user nào đã bấm link (log proxy).

## K06 – Trình bày cơ chế kỹ năng tổ chức
**Tình huống:** Họp 30 phút với chị Lan (HCNS) và anh Huy (CNTT).
**Vai diễn:** chị Lan hỏi "ai chịu trách nhiệm nếu kỹ năng hướng dẫn sai quy chế?"; anh Huy hỏi "làm sao không bị rác hàng nghìn kỹ năng?".
**Đầu ra:** sơ đồ vòng đời + chính sách duyệt + chỉ số đo.
**Thế nào là tốt:** có chủ sở hữu theo phòng ban, phạm vi, phiên bản, liên kết tài liệu nguồn, cơ chế hết hạn/ngừng dùng, ngưỡng đề xuất (≥ N kinh nghiệm), đo hiệu quả bằng A/B.

## K07 – Sự cố: câu trả lời bị cắt (INC-043)
**Tình huống:** Email E09. Chỉ câu dài (agent gọi nhiều tool) bị cắt; web và Teams đều bị.
**Gợi ý điều tra (đừng đọc trước khi tự thử):** <details><summary>mở</summary>reverse proxy `proxy_read_timeout` mặc định 60s; buffering SSE; timeout của custom endpoint trong LibreChat; timeout của tool MCP; Teams cần xử lý bất đồng bộ riêng.</details>
**Đầu ra:** thông báo sự cố (B4) trong 15 phút, postmortem (B5).

## K08 – Sự cố: chi phí gấp 3 (INC-044)
**Tình huống:** Email E06. Dữ liệu giả định tuần này: số câu hỏi chỉ tăng 20%.
**Gợi ý giả thuyết:** <details><summary>mở</summary>một agent mới gắn 40 tool → prompt to; top-k RAG tăng từ 5 lên 20; ai đó chèn ngày giờ vào đầu system prompt làm mất cache; vòng lặp agent do tool luôn trả "thử lại"; một user upload tài liệu 300 trang mỗi lần hỏi.</details>
**Đầu ra:** bảng phân rã chi phí (phòng × agent × model × input/output/cache), 3 nguyên nhân, 3 biện pháp có ước tính, email B8.

## K09 – Nâng cấp LibreChat thất bại
**Tình huống:** Sau khi đổi image sang bản mới, LibreChat không khởi động: log báo lỗi validate `librechat.yaml`.
**Nhiệm vụ:** rollback trong 15 phút (đã có backup?), đọc changelog tìm breaking change, sửa cấu hình trên môi trường thử, nâng cấp lại có checklist.
**Thế nào là tốt:** có backup trước khi nâng cấp; ghim tag image; checklist smoke test; ghi lại quy trình nâng cấp vào runbook.

## K10 – Demo cho Ban Giám đốc
**Tình huống:** 15 phút với anh Long (TGĐ) và chị Hạnh (GĐ Tài chính). Họ quan tâm: tiết kiệm được gì, rủi ro gì, mở rộng thế nào, tốn bao nhiêu.
**Vai diễn:** "Anh Long ngắt lời nếu thấy thuật ngữ, hỏi 'vậy công ty được gì'; chị Hạnh hỏi con số."
**Đầu ra:** kịch bản demo 6 bước (kế hoạch mục 4.3) + 1 slide số liệu pilot + lộ trình 3 tháng.
**Thế nào là tốt:** mở đầu bằng vấn đề và con số; demo phân quyền bằng 2 user; nói rõ giới hạn; đề xuất bước tiếp theo cụ thể cần họ quyết.

## K11 – So sánh hợp đồng gấp
**Tình huống:** Email E05. Tư liệu: `tu-lieu/hop-dong-v1.md`, `hop-dong-v2.md`.
**Đáp án (tự làm trước rồi mới mở):**
<details><summary>6 thay đổi có ý nghĩa</summary>

| # | Điều | v1 | v2 | Ảnh hưởng tới CTA |
|---|---|---|---|---|
| 1 | 2.3 (mới) | – | Bên A đơn phương chấm dứt, báo trước 15 ngày, không bồi thường | Rủi ro doanh thu cao |
| 2 | 3.3 | Thanh toán trong 15 ngày | 45 ngày | Dòng tiền chậm |
| 3 | 4 | Phản hồi sự cố Nghiêm trọng 4 giờ | 2 giờ | Tăng chi phí trực |
| 4 | 5 | Phạt 0,5%/lần, tối đa 5%, chỉ khi trễ khắc phục | 1%/lần, tối đa 12%, cả trễ phản hồi | Rủi ro phạt tăng mạnh |
| 5 | 6 | Tùy chỉnh thuộc Bên B, Bên A được dùng | Tùy chỉnh thuộc Bên A, phải bàn giao mã nguồn | Mất quyền sở hữu trí tuệ |
| 6 | 7 | Trách nhiệm tối đa 100% giá trị HĐ | 200% | Rủi ro bồi thường gấp đôi |

Thay đổi **không** có ý nghĩa (công cụ nên bỏ qua hoặc gom chung): định dạng địa chỉ hai bên, câu chữ Điều 1, "lỗi" → "bị lỗi" ở bảng SLA, câu chữ Điều 8, Điều 9.
Lưu ý: điều 2.3 mới mâu thuẫn tinh thần "chỉ chỉnh sửa câu chữ" của khách – công cụ tốt nên nêu điều này.
</details>

## K12 – Biên bản họp
**Tư liệu:** `tu-lieu/transcript-hop-du-an.md`.
<details><summary>Đáp án tham chiếu</summary>

**Quyết định:** (1) UAT lùi đến 27/11/2026; (2) vấn đề nhà cung cấp SMS OTP đóng – PNC chọn Tín Hiệu Việt.
**Việc cần làm:**
| Việc | Người | Hạn |
|---|---|---|
| Sửa lỗi trừ tiền hai lần (idempotency key) | Trịnh Văn Sơn | 19/11/2026 |
| Phản hồi khả năng thêm mã hợp đồng vào API hóa đơn | Đặng Thị Yến (PNC) | 20/11/2026 |
| Ước lượng phương án B (gọi API hợp đồng và ghép) | Mai Thị Ngọc | 18/11/2026 |
| Gửi email đề xuất 2 phương án go-live cho ông Phúc | Hoàng Minh Đức | 17/11/2026 |
| Gửi bộ dữ liệu ẩn danh mới | Đặng Thị Yến (PNC) | 23/11/2026 |
| Dựng môi trường UAT thứ hai | Trịnh Văn Sơn (ngầm định – nên đánh dấu "cần xác nhận") | chưa có hạn |
**Vấn đề còn mở:** ngày go-live (1/12 thu hẹp phạm vi hay 8/12) – chờ ông Phúc; thời hạn lưu log truy cập – chờ pháp chế PNC.
**Số liệu:** 214 test case, đã chạy 180, 11 lỗi mở (3 mức cao).
**Bẫy:** câu xin nghỉ của Lộc là chuyện cá nhân, không đưa vào biên bản; "thứ Năm" phải chuyển thành ngày cụ thể 19/11; việc của Sơn về môi trường UAT không được giao rõ.
</details>
