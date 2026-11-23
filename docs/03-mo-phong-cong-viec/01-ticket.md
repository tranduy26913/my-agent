# Mẫu ticket và backlog dự án "Trợ lý số SVT"

> Bối cảnh mô phỏng: bạn vừa vào SVT làm **AI Agent Engineer**, thuộc dự án nội bộ `NB-2026-01 – Trợ lý số SVT` (PM: Đỗ Quang Huy, Trưởng phòng CNTT). Backlog dưới đây là công việc bạn được giao, ánh xạ 1-1 với kế hoạch học 3 tuần. Mỗi ngày học = nhận ticket, làm, cập nhật trạng thái, viết phần "Kết quả" như ngoài đời.
>
> Có thể đưa backlog này vào GitHub Issues / Jira / Linear để luyện thao tác thật.

---

## 1. Mẫu ticket

### 1.1 Story / Task

```markdown
**[SVT-AI-___] <Động từ + kết quả>**   ví dụ: "Cho phép nhân viên hỏi số ngày phép qua Trợ lý"

| Trường | Giá trị |
|---|---|
| Loại | Story / Task / Spike / Bug / Incident |
| Người yêu cầu | <tên, phòng> |
| Người thực hiện | <bạn> |
| Ưu tiên | P1 / P2 / P3 |
| Ước lượng | <giờ hoặc story point> |
| Sprint / Ngày | |
| Liên kết | quy trình / tài liệu / ADR / PR |

**Bối cảnh (vì sao):** vấn đề nghiệp vụ, ai đau, đau thế nào, số liệu nếu có.
**Mô tả (cái gì):** phạm vi làm; **Ngoài phạm vi:** những gì không làm.
**Tiêu chí chấp nhận (Given/When/Then):**
- [ ] Given ..., When ..., Then ...
**Yêu cầu phi chức năng:** bảo mật, quyền, audit, độ trễ, chi phí.
**Cách kiểm thử / demo:**
**Rủi ro / câu hỏi mở:**
**Kết quả (điền khi xong):** đã làm gì, số liệu, link PR, việc còn lại.
```

### 1.2 Bug / Incident

```markdown
**[INC-___] <Triệu chứng ngắn gọn>**
| Mức độ | SEV1 (toàn hệ thống) / SEV2 (một nhóm người dùng) / SEV3 (một người, có cách làm tạm) |
| Phát hiện lúc | | Người báo | | Kênh | web / Teams / WhatsApp |
**Triệu chứng:** người dùng thấy gì (ảnh chụp, trace_id).
**Phạm vi ảnh hưởng:** bao nhiêu user, phòng nào, dữ liệu nào.
**Tái hiện:** các bước.
**Kỳ vọng / thực tế:**
**Xử lý tạm thời:**  **Nguyên nhân gốc:**  **Khắc phục lâu dài:**
**Bài học → ticket phòng ngừa:**
```

### 1.3 Spike (nghiên cứu có thời hạn)

```markdown
**[SPIKE-___] <Câu hỏi cần trả lời>**   Timebox: <x giờ>
**Câu hỏi:**  **Phương án đã xét:**  **Tiêu chí so sánh:**
**Kết luận + khuyến nghị:**  **Đầu ra:** ADR / note / bảng so sánh
```

---

## 2. Backlog theo giai đoạn

### Sprint 0 – Nền tảng (GĐ0, ngày 1–2)

**SVT-AI-001 · Task · P1 – Dựng LibreChat môi trường dev**
- Người yêu cầu: Đỗ Quang Huy (CNTT)
- Bối cảnh: Ban Giám đốc đã phê duyệt thử nghiệm "Trợ lý số SVT" trên nền LibreChat. Cần môi trường dev trong tuần này.
- Tiêu chí chấp nhận:
  - [ ] `docker compose up -d` chạy đủ service; có sơ đồ service + cổng trong `docs/notes/`.
  - [ ] Nối model Claude; tạo 1 admin + 5 user theo persona trong `data/README.md`.
  - [ ] `librechat.yaml`, `.env.example`, `docker-compose.override.yml` nằm trong repo, không có bí mật.
- Ngoài phạm vi: SSO, MCP.

**SVT-AI-002 · Task · P2 – Phân quyền tính năng theo role và ngân sách token**
- Tiêu chí: role `NHAN_VIEN` không tạo được agent; role `POWER_USER` tạo và chia sẻ được; balance bật, user hết credit bị chặn với thông báo dễ hiểu.

**SPIKE-003 · 4 giờ – Đăng nhập SSO bằng OIDC**
- Câu hỏi: dùng Entra ID của công ty hay Keycloak làm IdP trung gian? Claims nào cần để biết phòng ban?
- Đầu ra: sơ đồ luồng OIDC + ADR-001.

**SPIKE-004 · 3 giờ – Vì sao LibreChat (so với Open WebUI, Dify)**
- Đầu ra: bảng so sánh 1 trang để PM trình Ban Giám đốc (xem email E02).

### Sprint 1 – Agent và MCP (GĐ1, ngày 3–7)

**SVT-AI-010 · Task · P1 – Agent loop tham chiếu (proof of understanding)**
- Bối cảnh: PM yêu cầu đội hiểu rõ cơ chế trước khi dùng Agents của LibreChat.
- Tiêu chí: vòng lặp tự viết, 3 tool, log từng message; có `max_steps`; tool lỗi trả `is_error`. Kèm note giải thích.

**SVT-AI-011 · Story · P1 – Nhân viên hỏi được số ngày phép còn lại**
- Người yêu cầu: Nguyễn Thị Lan (HCNS) – xem email E01.
- Bối cảnh: HCNS nhận ~120 câu hỏi/tháng về số ngày phép qua email/Zalo.
- Tiêu chí chấp nhận:
  - [ ] Given Lê Văn Bình đăng nhập, When hỏi "tôi còn bao nhiêu ngày phép", Then trả 7,5 ngày, kèm cách tính.
  - [ ] Given Lê Văn Bình, When hỏi "Hồ Thị Phương còn bao nhiêu phép", Then từ chối lịch sự.
  - [ ] Given Phạm Thu Hà (hr), When hỏi phép của NV017, Then trả kết quả.
  - [ ] Danh tính lấy từ header do LibreChat chèn, **không** từ tham số tool.
  - [ ] Mỗi lần gọi tool ghi audit (allow/deny).
- Ngoài phạm vi: tạo đơn nghỉ.

**SVT-AI-012 · Story · P2 – Tra cứu danh bạ nhân viên**
- Tiêu chí: tìm theo tên không dấu ("binh le"), theo phòng; không trả số điện thoại cho người ngoài phòng (che PII); không trả nhân viên đã nghỉ việc.

**SVT-AI-013 · Task · P2 – Agent-service làm custom endpoint**
- Tiêu chí: API tương thích OpenAI có streaming; LibreChat hiển thị như một endpoint; agent-service gọi hr-mcp qua MCP client tự viết.

**SVT-AI-014 · Spike · 3 giờ – Ảnh hưởng của số lượng tool đến độ chính xác**
- Đầu ra: bảng 5 / 15 / 40 tool → tỉ lệ chọn đúng tool trên 20 câu hỏi.

### Sprint 2 – Kho tri thức (GĐ2, ngày 8–11)

**SVT-AI-020 · Story · P1 – Hỏi đáp quy chế công ty có trích dẫn**
- Người yêu cầu: Nguyễn Thị Lan (HCNS), Bùi Văn Tâm (TCKT).
- Tiêu chí chấp nhận:
  - [ ] Nạp 13 tài liệu trong `data/knowledge/` (trừ TL-099 ở lần đầu).
  - [ ] Câu trả lời có trích dẫn dạng "Quy chế nghỉ phép 01/2026/QĐ-SVT, Điều 4".
  - [ ] Không trả lời theo văn bản hết hiệu lực trừ khi được hỏi trực tiếp về nó.
  - [ ] Q17/Q18, Q21/Q22, Q29/Q30 trong golden set đúng hành vi.

**SVT-AI-021 · Task · P1 – Hybrid search + RRF + lọc quyền trong SQL**
- Tiêu chí: Q03, Q14 (số hiệu, viết tắt) trả đúng tài liệu ở top-3.

**SVT-AI-022 · Story · P2 – Nạp văn bản scan bằng OCR on-prem**
- Người yêu cầu: Nguyễn Thị Lan – "phần lớn thông báo cũ của công ty là bản scan có dấu đỏ".
- Tiêu chí: `scan/SVT-TB-018...pdf` được phát hiện là trang ảnh, OCR, nạp được; CER < 5% so với `ground-truth.md`; Q08, Q09 đúng.
- Ràng buộc: dữ liệu không rời máy chủ (Chính sách SVT-CS-007).

**SVT-AI-023 · Story · P2 – Trích xuất phiếu công tác phí từ ảnh scan**
- Người yêu cầu: Ngô Thị Mai (TCKT) – xem email E04.
- Tiêu chí: 2 file PNG → JSON đúng schema; phiếu NV018 bị gắn cờ đủ 4 vi phạm như `ground-truth.md`; có trường `do_tin_cay` và chuyển người duyệt khi thấp.

**SVT-AI-024 · Task · P1 – Bộ eval chạy bằng một lệnh**
- Tiêu chí: in recall@5, MRR, tỉ lệ hành vi đúng (trả lời / từ chối / không có thông tin), lưu kết quả theo ngày; README có bảng trước/sau cho ít nhất 3 thay đổi.

**SEC-025 · Bug · P1 – Tài liệu chứa chỉ dẫn lạ** (mở vào ngày 11 – xem kịch bản K05)

### Sprint 3 – Kỹ năng, tự động hóa, kênh (GĐ3, ngày 12–15)

**SVT-AI-030 · Spike · 4 giờ – Thiết kế vòng đời kỹ năng tổ chức**
- Đầu ra: sơ đồ vòng đời, schema DB, chính sách duyệt, ADR-005. Trình bày cho HCNS và CNTT (kịch bản K06).

**SVT-AI-031 · Story · P2 – Agent rút kinh nghiệm sau nhiệm vụ và đề xuất kỹ năng**
- Tiêu chí: sau nhiệm vụ "kiểm tra phiếu công tác phí", agent ghi bài học; khi admin duyệt, user khác dùng được ngay; bài học không chứa tên/số tiền cụ thể.

**SVT-AI-032 · Story · P3 – Trợ lý thao tác trên cổng nội bộ giả lập**
- Bối cảnh: cổng "Đăng ký phòng họp" chưa có API (xem `tu-lieu/cong-noi-bo-dat-phong-hop.md`).
- Tiêu chí: agent đọc lịch trống và điền form đặt phòng; **hỏi xác nhận trước khi bấm "Đặt phòng"**.

**SVT-AI-033 · Story · P2 – Mini-app so sánh hợp đồng**
- Người yêu cầu: Lê Hoàng Nam (KD) – xem email E05.
- Tiêu chí: `tu-lieu/hop-dong-v1.md` vs `v2.md` → liệt kê thay đổi có ý nghĩa (đủ 6 thay đổi trong đáp án), bỏ qua thay đổi định dạng.

**SVT-AI-034 · Story · P2 – Mini-app biên bản họp**
- Tiêu chí: từ `tu-lieu/transcript-hop-du-an.md` sinh biên bản: quyết định, việc cần làm (ai–việc–hạn), vấn đề mở.

**SVT-AI-035 · Story · P2 – Hỏi Trợ lý từ Microsoft Teams (hoặc WhatsApp)**
- Tiêu chí: cùng câu hỏi số ngày phép từ Teams cho cùng kết quả như web; câu > 5 giây vẫn nhận được trả lời (xử lý bất đồng bộ); webhook gửi lại không tạo trả lời trùng.

### Sprint 4 – Production (GĐ4, ngày 16–17)

**SVT-AI-040 · Task · P1 – Triển khai lên máy chủ Linux sau reverse proxy, có TLS và CI**
**SVT-AI-041 · Task · P1 – Audit log mức tool + báo cáo chi phí theo phòng ban**
- Người yêu cầu: Vũ Thị Hạnh (GĐ Tài chính) – xem email E06.
**SVT-AI-042 · Task · P2 – 5 prompt mẫu cho phòng ban + 1 trang hướng dẫn sử dụng**
**INC-043 · SEV2 – Câu trả lời bị cắt giữa chừng sau khoảng 60 giây** (kịch bản K07)
**INC-044 · SEV2 – Chi phí tuần này gấp 3 tuần trước** (kịch bản K08)
**SVT-AI-045 · Task · P2 – Nâng cấp LibreChat lên bản mới** (kịch bản K09)

### Sprint 5 – Bàn giao (GĐ5, ngày 18–19)
**SVT-AI-050 · README, sơ đồ, ADR, video demo** · **SVT-AI-051 · Buổi demo cho Ban Giám đốc** (kịch bản K10)

---

## 3. Quy ước trạng thái
`Backlog → Sẵn sàng → Đang làm → Chờ review → Xong`. Ticket chỉ "Xong" khi tiêu chí chấp nhận được tích hết **và** có demo hoặc số liệu chứng minh.
