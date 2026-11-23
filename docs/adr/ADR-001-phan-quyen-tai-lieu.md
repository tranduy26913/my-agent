# ADR-001: Quy tắc phân quyền tài liệu trong kho tri thức

- Trạng thái: **Đã chấp nhận** (2026-11-21)
- Code: `backend/app/rag/acl.py` · Test: `backend/tests/test_rag_logic.py`

## Bối cảnh
Frontmatter mỗi văn bản có `pham_vi_truy_cap`, `phong_ban_duoc_xem`, `vai_tro_duoc_xem`. `data/README.md` để ngỏ
quy tắc cho `han-che` (AND hay OR). Một nhân viên có thể giữ **nhiều** vai trò (`hr|manager` trong `employees.csv`).

## Quyết định
| Phạm vi | Điều kiện xem |
|---|---|
| `cong-khai` | Mọi nhân viên `dang-lam` |
| `phong-ban` | Phòng ∈ `phong_ban_duoc_xem` **HOẶC** có vai trò ∈ `vai_tro_duoc_xem` |
| `han-che` | Phòng ∈ `phong_ban_duoc_xem` **VÀ** có vai trò ∈ `vai_tro_duoc_xem` (danh sách rỗng = bỏ qua điều kiện đó; cả hai rỗng = không ai xem) |

Kèm theo:
1. Nhân viên đã nghỉ việc: không xem gì.
2. **Không có ngoại lệ cho `admin`**: quản trị hệ thống ≠ được đọc quy chế lương (least privilege).
3. Giá trị phạm vi lạ hoặc cấu hình thiếu: **từ chối** (fail closed).
4. Danh tính lấy từ bảng `employees` theo email. Không bao giờ tin vai trò do client gửi.
5. Lọc **trong SQL** của từng nhánh truy xuất (lọc trước), không lọc kết quả sau khi truy xuất.

## Hệ quả
- Với QC-004 (lương, `han-che` [HCNS, BGD] × [hr, executive]): Phạm Thu Hà (HCNS, hr) xem được. Nguyễn Minh Anh
  (HCNS, employee) không xem được, dù cùng phòng: chặt hơn OR, đúng tinh thần tài liệu Mật.
- Quy tắc được cài **hai lần độc lập**: `acl_sql()` cho truy vấn, `can_read()` cho eval. Eval so hai bản trên
  golden set; nếu có rò quyền, `python -m app.rag.eval` trả exit code 1.
- Nếu sau này cần "admin xem mọi thứ để kiểm toán", làm thành quyền riêng có audit (break-glass), không sửa quy tắc chung.

---

# ADR-002: Backend tự sinh câu trả lời (tool `ask_knowledge`)

- Trạng thái: **Đã chấp nhận** (2026-11-21)
- Code: `backend/app/rag/answer.py`, `backend/app/knowledge_mcp.py`

## Bối cảnh
Có 2 cách đưa tri thức vào LibreChat qua MCP:
(a) tool trả chunk, để agent của LibreChat tự tổng hợp; (b) backend truy xuất **và** sinh câu trả lời.

## Quyết định
Chọn (b): MCP chỉ có một tool `ask_knowledge(question, as_of?)`.

## Lý do
- SVT-CS-007 Điều 5 cấm gửi nội dung **Mật** tới model cloud. Chỉ backend biết chunk nào Mật. Với (a), chunk Mật
  sẽ đi thẳng vào model của LibreChat.
- Kiểm tra trích dẫn, audit và eval đi qua cùng một đường code, nên eval đo đúng thứ chạy production.

## Hệ quả
- Gọi LLM 2 lần (agent LibreChat + backend): tốn thêm chi phí và độ trễ.
- P1: chunk Mật bị giữ lại, người có quyền chỉ nhận vị trí trích dẫn. Câu Q18, Q29 trong golden set chưa đạt
  **có chủ đích**. P3 sẽ định tuyến phần Mật sang model on-prem.
- LLM lỗi thì tool vẫn trả về danh sách nguồn liên quan, không văng lỗi về LibreChat.
