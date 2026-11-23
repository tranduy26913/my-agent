# Thuật ngữ AI Agent Engineer (Anh – Việt)

> Dùng khi đọc tài liệu gốc tiếng Anh và khi trả lời phỏng vấn. Cột "Nói thế nào khi phỏng vấn" là cách diễn đạt ngắn, đúng bản chất.

## Agent và tool calling

| Thuật ngữ | Nghĩa | Nói thế nào khi phỏng vấn |
|---|---|---|
| Agent | Hệ thống trong đó LLM tự quyết bước tiếp theo (gọi tool nào, khi nào dừng) | "Một vòng lặp: model đề xuất hành động, code thực thi, kết quả quay lại model" |
| Workflow | Luồng do code quyết định, LLM chỉ là một bước trong luồng | "Đường đi cố định, LLM xử lý từng ô" |
| Tool calling / function calling | Model sinh JSON yêu cầu gọi hàm; ứng dụng thực thi | "Model không chạy gì, nó chỉ *xin* chạy" |
| `tool_use` / `tool_result` | Khối nội dung yêu cầu gọi tool / khối trả kết quả (Anthropic API) | Ghép với nhau qua `tool_use_id` |
| `stop_reason` | Lý do model dừng sinh: `end_turn`, `tool_use`, `max_tokens`… | Điều kiện để vòng lặp quyết định đi tiếp hay dừng |
| Parallel tool calls | Một lượt model yêu cầu nhiều tool cùng lúc | Trả tất cả `tool_result` trong **một** message user |
| ReAct | Reason + Act: xen kẽ suy luận và hành động | Nền móng của hầu hết agent hiện nay |
| Plan-and-execute | Lập kế hoạch trước, thực thi từng bước, lập lại khi lỗi | Hợp với nhiệm vụ dài, dễ quan sát |
| Orchestrator–workers | Một agent chia việc cho các agent con | Dùng khi cần cô lập context hoặc chạy song song |
| Human-in-the-loop (HITL) | Người duyệt trước hành động có tác dụng phụ | "Đọc thì tự do, ghi/gửi/xóa thì xin phép" |
| Excessive agency | Agent có nhiều quyền/tool hơn mức cần | Một mục trong OWASP LLM Top 10 |

## Context và bộ nhớ

| Thuật ngữ | Nghĩa |
|---|---|
| Context window | Toàn bộ token model nhìn thấy trong một lần gọi |
| Context engineering | Chọn *cái gì* vào context, *khi nào*, *dưới dạng nào* |
| Context rot | Chất lượng giảm khi context quá dài, thông tin quan trọng bị "chìm" |
| Compaction | Tóm tắt lịch sử cũ để giải phóng context |
| Prompt caching | Tái sử dụng phần đầu prompt không đổi để giảm chi phí/độ trễ; vì vậy lịch sử nên append-only |
| Semantic memory | Tri thức (tài liệu, sự thật) |
| Episodic memory | Sự kiện đã xảy ra (lần trước làm gì, kết quả ra sao) |
| Procedural memory | Cách làm (skill, quy trình) |
| Progressive disclosure | Chỉ đưa tên + mô tả vào context, nội dung đầy đủ tải khi cần |

## MCP

| Thuật ngữ | Nghĩa |
|---|---|
| MCP (Model Context Protocol) | Chuẩn mở để ứng dụng AI kết nối tool và dữ liệu |
| Host / Client / Server | Ứng dụng AI / bộ kết nối 1-1 trong host / tiến trình cung cấp năng lực |
| Tools / Resources / Prompts | Hàm model gọi được / dữ liệu ứng dụng đọc được / mẫu prompt người dùng chọn |
| Sampling / Elicitation | Server xin host gọi LLM hộ / server xin hỏi thêm người dùng |
| stdio / Streamable HTTP | Transport local qua stdin-stdout / transport remote qua HTTP (có thể stream SSE) |
| JSON-RPC 2.0 | Định dạng message: `{jsonrpc, id, method, params}` |
| Tool poisoning | Mô tả tool chứa chỉ dẫn độc hại lái model |
| Confused deputy | Server có quyền cao bị lừa làm việc thay cho người không có quyền |

## RAG và tài liệu

| Thuật ngữ | Nghĩa |
|---|---|
| RAG | Truy xuất tài liệu liên quan rồi đưa vào context để model trả lời |
| Embedding | Vector biểu diễn ngữ nghĩa của đoạn văn |
| Chunk / chunking | Mẩu tài liệu / cách cắt tài liệu |
| Bi-encoder / cross-encoder | Mã hóa riêng câu hỏi và tài liệu (nhanh) / chấm điểm cặp (chậm, chính xác) – dùng làm reranker |
| ANN, HNSW, IVF | Tìm kiếm gần đúng; hai loại chỉ mục phổ biến trong pgvector |
| BM25 / full-text search | Tìm theo từ khóa |
| Hybrid search | Kết hợp vector + từ khóa |
| RRF (Reciprocal Rank Fusion) | Gộp nhiều danh sách theo thứ hạng: `Σ 1/(k + rank)` |
| Contextual retrieval | Thêm đoạn mô tả ngữ cảnh vào chunk trước khi embed |
| Parent–child chunk | Tìm bằng chunk nhỏ, trả về đoạn cha lớn hơn |
| Golden set | Bộ câu hỏi chuẩn kèm đáp án/tài liệu đúng để đo |
| recall@k, MRR | Tỉ lệ câu có tài liệu đúng trong top-k / trung bình nghịch đảo thứ hạng tài liệu đúng đầu tiên |
| Faithfulness | Câu trả lời có bám đúng tài liệu truy xuất không |
| LLM-as-judge | Dùng LLM chấm điểm đầu ra |
| OCR | Nhận dạng chữ từ ảnh |
| Indirect prompt injection | Chỉ dẫn độc hại nằm trong dữ liệu (tài liệu, web, email) mà agent đọc |

## Vận hành

| Thuật ngữ | Nghĩa |
|---|---|
| OIDC / SAML / LDAP | Các giao thức đăng nhập tập trung |
| Entra ID | Tên mới của Azure AD |
| On-Behalf-Of (OBO) | Đổi token của user lấy token gọi API khác *thay mặt* user |
| RBAC / ABAC | Phân quyền theo vai trò / theo thuộc tính (phòng ban, cấp độ mật…) |
| Audit log | Nhật ký ai làm gì, lúc nào, trên dữ liệu nào |
| Observability / tracing | Quan sát từng bước bên trong hệ thống (span, trace) |
| Guardrail | Lớp kiểm tra đầu vào/đầu ra |
| PII | Thông tin định danh cá nhân |
| SSE | Server-Sent Events – cơ chế streaming một chiều qua HTTP |
| Idempotency | Gọi lại nhiều lần không gây tác dụng phụ lặp |
| ADR | Architecture Decision Record – ghi lại một quyết định kiến trúc |
| ROI | Lợi ích thu về so với chi phí bỏ ra |
