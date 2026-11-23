# Agent, tool calling, mẫu thiết kế và context (GĐ1, ngày 3–5, 7)

## 1. Bản chất tool calling

**Model không thực thi gì.** Nó chỉ sinh ra một khối có cấu trúc nói "tôi muốn gọi tool X với input Y". Code của bạn quyết định có chạy không, chạy rồi gửi kết quả về.

Một lượt đầy đủ (định dạng Anthropic Messages API, rút gọn):

```text
→ request 1
  tools: [{name: "get_leave_balance", description: "...", input_schema: {...}}]
  messages: [{role: user, content: "Tôi còn mấy ngày phép?"}]

← response 1   stop_reason = "tool_use"
  content: [ {type: text, text: "Để tôi kiểm tra."},
             {type: tool_use, id: "toolu_01", name: "get_leave_balance", input: {}} ]

→ request 2   (gửi lại TOÀN BỘ lịch sử + kết quả)
  messages: [ user(câu hỏi),
              assistant(nguyên content của response 1),
              user([{type: tool_result, tool_use_id: "toolu_01", content: "còn 7.5 ngày"}]) ]

← response 2   stop_reason = "end_turn"
  content: [{type: text, text: "Bạn còn 7,5 ngày phép năm 2026."}]
```

Điểm phải nói được:
- API **không có trạng thái**: mỗi request gửi lại toàn bộ hội thoại.
- `tool_use_id` nối yêu cầu với kết quả. Nhiều tool song song → trả **tất cả** `tool_result` trong **một** message user.
- Tool lỗi → trả `tool_result` với `is_error: true` và thông điệp hữu ích ("không tìm thấy nhân viên mã NV999; hãy dùng search_employee theo tên"). Model sẽ tự sửa.
- OpenAI dùng tên khác (`tool_calls`, role `tool`, `finish_reason`), bản chất giống hệt.

## 2. Agent loop tối giản (mã giả)

```text
messages = [user_input]
for step in range(MAX_STEPS):
    resp = llm(system, tools, messages)
    messages.append(assistant: resp.content)
    if resp.stop_reason != "tool_use": return resp.text
    results = [run_tool(call) for call in resp.tool_calls]   # có thể song song
    messages.append(user: results)
raise "Vượt số bước tối đa"
```

Thứ làm nó thành "production": giới hạn bước **và** ngân sách token/thời gian, timeout mỗi tool, log từng bước (trace), xác nhận người dùng trước tool có tác dụng phụ, cắt bớt kết quả tool quá dài.

## 3. Thiết kế tool tốt (tool = prompt)

| Nguyên tắc | Ví dụ xấu → tốt |
|---|---|
| Tên rõ, có namespace | `get` → `hr_get_leave_balance` |
| Mô tả nói *khi nào* dùng và *khi nào không* | "Lấy dữ liệu" → "Trả số ngày phép còn lại của một nhân viên trong năm hiện tại. Không dùng để xem lịch sử đơn nghỉ." |
| Tham số ít, kiểu chặt, có enum | `type: string` → `enum: ["annual","sick","unpaid"]` |
| Gộp theo nhiệm vụ, không theo bảng DB | 3 tool `get_user`, `get_dept`, `get_manager` → 1 tool `lookup_employee` trả cả thông tin cần thiết |
| Kết quả ngắn, có ngữ nghĩa | trả 50 cột UUID → trả tên, chức danh, phòng ban; có tham số `detail_level` |
| Lỗi có hướng dẫn sửa | "500 Internal Error" → "Ngày bắt đầu sau ngày kết thúc; định dạng YYYY-MM-DD" |

Quá nhiều tool (30–40+) làm giảm độ chính xác chọn tool → thu gọn, namespace, tool search, hoặc chia cho sub-agent.

## 4. Workflow hay agent

| Tiêu chí | Workflow | Agent |
|---|---|---|
| Các bước biết trước? | Có | Không, phụ thuộc dữ liệu giữa chừng |
| Cần tất định, kiểm toán | Rất hợp | Khó hơn |
| Chi phí, độ trễ | Thấp, dự đoán được | Cao, biến động |
| Ví dụ doanh nghiệp | Phân loại email → trích xuất → ghi hệ thống | Trợ lý trả lời câu hỏi phức tạp phải tra nhiều nguồn |

Quy tắc: **bắt đầu bằng thứ đơn giản nhất chạy được** (một lời gọi LLM có RAG), chỉ tăng độ tự chủ khi đo thấy cần.

### Năm mẫu (Anthropic *Building effective agents*)
1. **Prompt chaining** – chuỗi bước cố định, có cổng kiểm tra giữa các bước.
2. **Routing** – phân loại đầu vào rồi chuyển đến nhánh chuyên biệt (model rẻ cho câu dễ).
3. **Parallelization** – chia nhỏ chạy song song (sectioning) hoặc chạy nhiều lần lấy biểu quyết (voting).
4. **Orchestrator–workers** – điều phối viên chia việc động cho worker.
5. **Evaluator–optimizer** – một bên sinh, một bên chấm và góp ý, lặp đến khi đạt.

### Lập kế hoạch
- **ReAct**: Thought → Action → Observation lặp lại.
- **Plan-and-execute**: lập danh sách bước (tool `update_plan`), thực thi, đánh dấu xong, lập lại khi gặp lỗi.
- **Sub-agent**: giao một nhiệm vụ con cho agent có context riêng sạch, chỉ nhận lại bản tóm tắt → tránh làm đầy context của agent chính.

## 5. Context engineering

Context là ngân sách. Mọi thứ vào context đều tốn tiền, tăng độ trễ và có thể làm model "lạc".

| Vấn đề | Kỹ thuật |
|---|---|
| Lịch sử dài | Cửa sổ trượt; **compaction** (tóm tắt phần cũ, giữ quyết định, việc dở dang) |
| Kết quả tool to | Cắt, phân trang, trả tóm tắt + id để đọc thêm |
| Nhiều tài liệu | RAG thay vì nhét cả; contextual retrieval |
| Nhiều kỹ năng | Progressive disclosure (chỉ tên + mô tả) |
| Nhiệm vụ dài | File ghi chú/todo làm bộ nhớ làm việc; sub-agent |
| Chi phí lặp | Prompt caching: system + tools + lịch sử cố định ở đầu, **không sửa giữa chừng** |

### Bộ nhớ dài hạn

| Loại | Câu hỏi nó trả lời | Ví dụ trong demo |
|---|---|---|
| Semantic | "Sự thật là gì?" | knowledge-mcp (quy chế, tài liệu) |
| Episodic | "Lần trước chuyện gì đã xảy ra?" | `record_lesson`, `search_experiences` |
| Procedural | "Làm việc này thế nào?" | Skills của LibreChat (SKILL.md) + experience-mcp |
| Hồ sơ người dùng | "Người này thích/cần gì?" | User Memory của LibreChat |

Câu hỏi thiết kế bộ nhớ: lưu gì (không lưu mọi thứ), khi nào ghi (cuối nhiệm vụ, khi user sửa), khi nào đọc (đầu nhiệm vụ), ai được xem, hết hạn thế nào, sửa/xóa thế nào.

## 6. Ba cách xây agent – nên so sánh được

| | Agents của LibreChat | Agent loop tự viết | Framework (LangGraph, SDK tool runner) |
|---|---|---|---|
| Làm hộ | UI, quản lý agent, gắn MCP, chia sẻ | Không gì | Vòng lặp, trạng thái, checkpoint, retry |
| Che giấu | Cách build context, cắt lịch sử | Không gì | Một phần luồng điều khiển |
| Khi dùng | Người dùng nghiệp vụ tự tạo agent | Cần kiểm soát tuyệt đối, học bản chất | Luồng phức tạp, nhiều nhánh, cần resume |

## 7. Lỗi kinh điển và cách xử lý

| Triệu chứng | Nguyên nhân thường gặp | Xử lý |
|---|---|---|
| Lặp vô hạn | Tool luôn trả "thử lại"; không có điều kiện dừng | `max_steps`, phát hiện lặp cùng call, ngân sách token |
| Gọi sai tool | Mô tả mơ hồ, tool trùng chức năng, quá nhiều tool | Viết lại mô tả, gộp tool, routing |
| Bịa tham số | Schema lỏng, thiếu tool tra cứu | Enum, tool `search_*` trước `get_*` |
| Bỏ qua kết quả tool | Kết quả quá dài, lẫn nhiễu | Thu gọn kết quả, định dạng rõ |
| Hành động nguy hiểm | Không có HITL | Danh sách tool cần xác nhận |

## Câu hỏi tự kiểm
1. Viết lại từ trí nhớ 4 message của một lượt tool calling có 2 tool song song.
2. Vì sao tool lỗi nên trả `is_error` thay vì ném exception làm sập vòng lặp?
3. Cho 3 bài toán của phòng Nhân sự, phân loại workflow hay agent và giải thích.
4. Vì sao không nên chèn thời gian hiện tại vào đầu system prompt nếu muốn dùng prompt cache?

## Nguồn
- Anthropic docs: *Tool use*; Anthropic Engineering: *Building effective agents*, *Writing effective tools for agents*, *Effective context engineering for AI agents*.
- Yao et al. 2022 *ReAct*; Packer et al. 2023 *MemGPT*; Lilian Weng 2023 *LLM Powered Autonomous Agents*.
