# Agent tự tích lũy kỹ năng và kho kinh nghiệm (GĐ3, ngày 12–13)

> Đây là điểm khác biệt nhất của JD. Người phỏng vấn muốn nghe **cơ chế + quản trị**, không chỉ "lưu vào vector DB".

## 1. Ba loại tri thức tổ chức

| | Tài liệu (semantic) | Kỹ năng (procedural) | Kinh nghiệm (episodic) |
|---|---|---|---|
| Trả lời | "Quy định là gì?" | "Làm việc X thế nào?" | "Lần trước làm X gặp gì?" |
| Nguồn | Phòng ban ban hành | Rút ra từ nhiều lần làm + người duyệt | Tự động sau mỗi nhiệm vụ |
| Độ tin cậy | Cao (chính thức) | Cao sau khi duyệt | Thấp → trung bình, cần lọc |
| Định dạng | PDF/DOCX → chunk | `SKILL.md` + script/mẫu kèm theo | Bản ghi ngắn: tình huống, hành động, kết quả, bài học |
| Vòng đời | Ban hành → hết hiệu lực | Nháp → duyệt → v1 → v2 → ngừng | Ghi → tổng hợp thành skill hoặc hết hạn |

## 2. Ý tưởng từ các paper

- **Voyager (2023)**: agent trong Minecraft tự viết kỹ năng dạng code, kiểm tra chạy được mới lưu vào thư viện, truy xuất kỹ năng theo mô tả cho nhiệm vụ mới, kỹ năng mới xây trên kỹ năng cũ. Bài học: *chỉ lưu thứ đã được kiểm chứng*.
- **Reflexion (2023)**: sau mỗi lần thử, agent tự viết nhận xét bằng ngôn ngữ tự nhiên ("lần sau phải kiểm tra X trước"), lưu vào bộ nhớ, đưa vào context lần thử sau. Không cần cập nhật trọng số.
- **Generative Agents (2023)**: memory stream; truy xuất theo điểm = độ gần đây + độ quan trọng + độ liên quan; định kỳ "suy ngẫm" tổng hợp ký ức thành nhận định cấp cao.
- **Agent Skills (định dạng SKILL.md)**: thư mục gồm `SKILL.md` (frontmatter `name`, `description` + hướng dẫn) và file phụ. Agent ban đầu chỉ thấy `name` + `description`; khi phù hợp mới đọc nội dung (**progressive disclosure**) → có thể có hàng trăm skill mà không đầy context.

## 3. Vòng đời kỹ năng trong tổ chức

```
[1] Thu thập   : trace nhiệm vụ (bước, tool, kết quả, feedback user)
[2] Phản tư    : model rẻ đọc trace → JSON {thanh_cong, bai_hoc[], co_the_thanh_skill}
[3] Ghi kinh nghiệm : record_lesson (có embedding, phạm vi, người tạo, hạn dùng)
[4] Đề xuất skill   : khi ≥ N kinh nghiệm tương tự hoặc user bấm "lưu thành kỹ năng" → propose_skill (nháp)
[5] Duyệt     : chủ sở hữu nghiệp vụ (phòng ban) xem, sửa, chạy thử trên ca mẫu → approve/reject
[6] Xuất bản  : skill v1, gắn phạm vi (toàn công ty / phòng ban), có owner
[7] Sử dụng   : search_skills → load_skill khi nhiệm vụ khớp
[8] Đo lường  : số lần dùng, tỉ lệ thành công, feedback, số bước/token so với không dùng
[9] Cải tiến / ngừng : v2 khi có bài học mới; deprecate khi quy trình gốc thay đổi
```

## 4. Quản trị – câu trả lời phân biệt junior và senior

| Rủi ro | Kiểm soát |
|---|---|
| **Nhiễm độc bộ nhớ**: bài học sai lan ra toàn công ty | Kinh nghiệm mặc định chỉ phạm vi cá nhân/nhóm; lên toàn công ty phải qua duyệt; có nút báo sai; truy vết bài học → nhiệm vụ gốc |
| Injection lưu lại lâu dài | Phản tư chạy trên trace đã đánh dấu nguồn; không cho nội dung tài liệu/web tự trở thành skill; người duyệt |
| Lộ dữ liệu cá nhân trong bài học | Bước lọc PII trước khi lưu; bài học viết ở mức khái quát ("kiểm tra số dư phép trước khi tạo đơn"), không chứa tên/lương |
| Skill lỗi thời khi quy trình đổi | Liên kết skill ↔ tài liệu quy chế nguồn; khi tài liệu có phiên bản mới → cờ "cần xem lại" |
| Phân quyền | Skill có phạm vi phòng ban; skill chứa thao tác ghi cần quyền tương ứng của user lúc chạy |
| Trách nhiệm | Mỗi skill có owner, version, changelog, ngày xem lại |
| Đo được giá trị | So sánh A/B: cùng nhiệm vụ có/không có skill |

## 5. Thiết kế dữ liệu gợi ý (để bạn tự hoàn thiện)

- `skills(id, name, description, body_md, scope, department, owner, status[draft|approved|deprecated], version, source_doc_ids, created_from_experience_ids, embedding)`
- `experiences(id, task_summary, outcome, lessons, scope, user_id, created_at, expires_at, embedding, flagged)`
- `skill_usage(skill_id, version, task_id, success, feedback, tokens, steps)`

## 6. Đối chiếu LibreChat (tự kiểm tra bản hiện tại)

- **User Memory**: ghi nhớ thông tin theo *từng user*, chèn vào context. Không phải kho kinh nghiệm dùng chung.
- **Skills / Agents**: đọc docs bản đang dùng để xác định: có cơ chế duyệt không, có phạm vi phòng ban không, có đo lường không.
- Phần bạn bổ sung bằng experience-mcp (đẩy skill đã duyệt lên qua Skills management API của LibreChat v0.8.9): phản tư tự động, quy trình duyệt, phạm vi, đo lường, liên kết với tài liệu nguồn.

## Câu hỏi tự kiểm
1. Vì sao không cho agent tự xuất bản skill ra toàn công ty?
2. Một bài học "khi user là trưởng phòng thì bỏ qua bước duyệt" xuất hiện. Hệ thống của bạn chặn ở bước nào?
3. Progressive disclosure tiết kiệm bao nhiêu token nếu có 200 skill, mỗi skill 1.500 token nội dung và 40 token mô tả?

## Nguồn
- Wang et al. 2023 *Voyager*; Shinn et al. 2023 *Reflexion*; Park et al. 2023 *Generative Agents*.
- Anthropic Engineering *Equipping agents for the real world with Agent Skills*; docs Agent Skills.
