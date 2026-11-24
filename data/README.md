# Bộ dữ liệu giả lập: Công ty A (CTA)

> **Toàn bộ là dữ liệu hư cấu** dùng để học và demo: tên người, công ty, khách hàng, số điện thoại, mã số thuế, domain `cty-a.example` đều không có thật. Trích dẫn luật (Bộ luật Lao động 2019…) chỉ mang tính minh họa, đừng dùng làm tư vấn pháp lý.

Mục đích: có một "doanh nghiệp" đủ thật để xây và kiểm thử **hr-mcp**, **knowledge-mcp**, phân quyền, OCR, eval và các kịch bản tự động hóa.

## 1. Cấu trúc

```
data/
├─ knowledge/        14 tài liệu Markdown có frontmatter metadata → nạp vào knowledge-mcp
├─ scan/             PDF/PNG scan giả lập (không có lớp text) + ground-truth.md (đáp án OCR)
├─ hr/               CSV cho hr-mcp: nhân viên, số dư phép, đơn nghỉ, lương (MẬT), dự án
└─ eval/             golden-set.jsonl: 35 câu hỏi có đáp án, người hỏi, tài liệu đúng
```

## 2. Công ty và người dùng mẫu

| Phòng | Mã | Trưởng phòng | Nhân sự mẫu |
|---|---|---|---|
| Ban Giám đốc | BGD | Phạm Đức Long (TGĐ) | Vũ Thị Hạnh (GĐ Tài chính) |
| Hành chính – Nhân sự | HCNS | Nguyễn Thị Lan | Phạm Thu Hà (C&B), Trần Quốc Bảo, Nguyễn Minh Anh |
| Tài chính – Kế toán | TCKT | Bùi Văn Tâm | Ngô Thị Mai, Lương Văn Hùng |
| CNTT | CNTT | Đỗ Quang Huy | Đặng Văn Khoa, Vương Thị Thảo |
| Kinh doanh | KD | Lê Hoàng Nam | Lê Văn Bình, Hồ Thị Phương, Cao Minh Trí (thử việc) |
| Dự án | DA | Trần Thu Trang | Hoàng Minh Đức (PM), Trịnh Văn Sơn, Mai Thị Ngọc… |

**Bộ persona nên tạo thành tài khoản LibreChat để demo phân quyền:**

| Persona | Email | Vai trò hệ thống | Dùng để thử |
|---|---|---|---|
| Nhân viên KD | binh.le@cty-a.example | employee | Không xem được lương, quy trình TCKT, hồ sơ dự án nội bộ DA |
| Chuyên viên C&B | ha.pham@cty-a.example | hr | Xem quy chế lương, số dư phép của người khác |
| Kế toán | mai.ngo@cty-a.example | employee (TCKT) | Xem quy trình thanh toán, không xem dự án PNC |
| PM dự án | duc.hoang@cty-a.example | manager (DA) | Duyệt đơn nghỉ của cấp dưới, xem hồ sơ dự án |
| Trưởng phòng CNTT | huy.do@cty-a.example | manager, admin | Quản trị |

## 3. Mô hình phân quyền tài liệu (frontmatter)

| Trường | Ý nghĩa |
|---|---|
| `pham_vi_truy_cap` | `cong-khai` (mọi nhân viên) · `phong-ban` (chỉ phòng trong `phong_ban_duoc_xem`, **hoặc** user có vai trò trong `vai_tro_duoc_xem`) · `han-che` (phải thuộc phòng trong `phong_ban_duoc_xem` **và/hoặc** có vai trò trong `vai_tro_duoc_xem` – bạn tự quyết quy tắc và ghi vào ADR) |
| `hieu_luc_tu`, `het_hieu_luc` | Mặc định chỉ truy xuất tài liệu đang hiệu lực tại ngày hỏi |
| `thay_the`, `bi_thay_the_boi` | Liên kết phiên bản |
| `phan_loai_bao_mat` | `Mat` → chỉ được gửi tới model on-prem theo Chính sách CTA-CS-007 Điều 5 (bài tập routing model) |
| `muc_dich_thu_nghiem` | Tài liệu cố ý chứa tấn công – xem mục 5 |

Ma trận quyền tóm tắt:

| Tài liệu | Ai xem được |
|---|---|
| QC-001 Nội quy, QC-002/003 Nghỉ phép, QD-005 Công tác phí, CS-007 ATTT & AI, HD-008 CNTT, HD-009 Sổ tay, FAQ-013, TL-099, TB-018 (scan) | Mọi nhân viên |
| QC-004 Lương thưởng (Mật) | HCNS, BGD (vai trò hr, executive) |
| QT-006 Mua sắm – thanh toán | TCKT, BGD |
| QT-010 Tuyển dụng | HCNS, BGD, mọi user vai trò `manager` |
| DA-011 Hồ sơ dự án PNC (Mật) | DA, KD, BGD |
| DA-012 Biên bản họp PNC | DA, BGD |

## 4. Những "bẫy" được cài sẵn (để thí nghiệm có ý nghĩa)

| Bẫy | Ở đâu | Kiểm tra điều gì |
|---|---|---|
| Hai phiên bản quy chế nghỉ phép (12 ngày → 14 ngày) | QC-002, QC-003 | Lọc hiệu lực, phiên bản |
| Truy vấn theo số hiệu văn bản | "12/2023/QĐ-CTA", "08/2025/QĐ-CTA" | Hybrid search |
| Từ đồng nghĩa / viết tắt | "lấy vợ" ↔ "kết hôn"; "CTP" ↔ "công tác phí" | Vector vs full-text |
| Cùng thông tin ở tài liệu công khai và tài liệu Mật | Ngày trả lương, thưởng giới thiệu (FAQ-013 và QC-004) | Trích dẫn đúng nguồn được phép |
| Quy định bị ghi đè tạm thời | Giờ làm việc: QC-001 và thông báo scan TB-018 | OCR + suy luận theo thời điểm |
| Bảng trong Markdown | QC-004, QT-006, HD-008 | Chunking không cắt vỡ bảng |
| Prompt injection gián tiếp | TL-099 (comment HTML + chữ trắng cỡ 1px) | Phòng thủ nhiều lớp |
| Nhân viên đã nghỉ việc | NV026 `da-nghi-viec` | hr-mcp không trả như nhân viên đang làm |
| Nhân viên thử việc vào giữa năm | NV019 – phép năm tính tỷ lệ | Logic nghiệp vụ |
| Đơn nghỉ cần xử lý | `leave_requests.csv` trạng thái `cho-duyet` (có đơn 9 ngày thiếu kế hoạch bàn giao, đơn kết hôn) | Kịch bản agent hỗ trợ quản lý duyệt đơn |
| Phiếu công tác phí vi phạm | `scan/de-nghi-thanh-toan-CTP-NV018.png` | Trích xuất + validate + chuyển người duyệt |

## 5. Tài liệu thử nghiệm prompt injection
`CTA-TL-099` trông như một thông báo bình thường nhưng chứa chỉ dẫn độc hại trong comment HTML và đoạn chữ ẩn. Trong ngày 8–10 có thể **loại nó khỏi lần nạp đầu**, đến ngày 11 mới nạp vào để làm thí nghiệm. Câu Q32, Q33 trong golden set kiểm tra hành vi.

## 6. Dữ liệu hr/

| File | Nội dung | Ghi chú |
|---|---|---|
| `employees.csv` | 24 nhân viên: mã, tên, email, phòng, chức danh, cấp bậc, quản lý trực tiếp, vai trò hệ thống, ngày vào làm, loại HĐ, trạng thái, số điện thoại | `vai_tro` nhiều giá trị ngăn cách bằng `|` |
| `leave_balances.csv` | Số dư phép năm 2026 | `con_lai = duoc_huong + ton - ton_da_huy - da_su_dung`; tính theo QC-003 |
| `leave_requests.csv` | ~140 đơn nghỉ 2026 | Tổng đơn `phep-nam` đã duyệt của mỗi người khớp `da_su_dung` |
| `salaries_MAT.csv` | Lương cơ bản, phụ cấp, xếp loại KPI | **MẬT** – chỉ vai trò `hr`/`executive`; không đưa nội dung vào log |
| `projects.csv`, `project_members.csv` | 4 dự án, thành viên | Có dự án nội bộ NB-2026-01 "Trợ lý số CTA" |

Mốc thời gian dữ liệu: **20/11/2026**. Ví dụ để tự kiểm: NV017 Lê Văn Bình còn **7,5 ngày** phép.

## 7. Golden set (`eval/golden-set.jsonl`)

Mỗi dòng: `id, cau_hoi, nguoi_hoi, loai, tai_lieu_dung, vi_tri, dap_an_tham_chieu, hanh_vi_mong_doi, ghi_chu`.

- `loai`: su-kien, phien-ban, so-hieu, dong-nghia, viet-tat, suy-luan, tinh-toan, theo-thoi-diem, scan-ocr, phan-quyen, injection, khong-co-thong-tin.
- `hanh_vi_mong_doi`: `tra-loi` · `tu-choi-khong-quyen` · `khong-co-thong-tin`.
- Đo **truy xuất** bằng `tai_lieu_dung` (recall@k theo doc_id; mở rộng thành chunk_id khi bạn đã cố định cách chunk).
- Đo **phân quyền** bằng các cặp cùng câu hỏi khác người hỏi: Q17/Q18, Q21/Q22, Q29/Q30. Với ca từ chối: kiểm tra **log truy xuất không chứa chunk bị cấm**, không chỉ kiểm tra câu trả lời.
- Nên tự viết thêm câu hỏi đến khoảng 50 câu khi đã nạp xong, và giữ một phần làm tập "không nhìn" (held-out) để tránh tối ưu quá mức.
