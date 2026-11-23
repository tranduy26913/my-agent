# Kế hoạch 3 tuần: từ Web/C# Developer đến AI Agent Engineer (nền LibreChat)

> Mục tiêu: nắm **bản chất** từng mảng kiến thức trong JD, tự xây một sản phẩm demo trên nền **LibreChat** (mã nguồn mở) với phần lõi tự viết bằng Python, và đủ tự tin trả lời phỏng vấn ở mức "người xây hệ thống".

**Phạm vi:** đã bỏ phần nền tảng LLM / prompt engineering / Python cơ bản (bạn đã nắm). Kế hoạch bắt đầu thẳng từ việc dựng nền tảng và xây agent.

---

## 0. Cách dùng kế hoạch này

**Thời lượng:** 19 ngày học + 2 ngày dự phòng (khoảng 3 tuần). Giả định khoảng 3 giờ/ngày thường và 5–6 giờ/ngày cuối tuần.

**Bốn bước cho mỗi khái niệm:**

1. **Đọc từ nguồn gốc**: tài liệu chính thức, paper, spec, và **mã nguồn LibreChat**.
2. **Tự viết bản tối giản**: ví dụ tự viết agent loop trước khi dùng Agents của LibreChat, để biết LibreChat đang làm gì bên dưới.
3. **Làm thí nghiệm "phá"**: cố tình làm sai để thấy hệ thống hỏng ở đâu và vì sao.
4. **Giải thích lại bằng lời của mình**: viết 1 trang note mỗi chủ đề vào `docs/notes/`. Các note này là tài liệu ôn phỏng vấn.

**Nguyên tắc với LibreChat: không fork, không sửa lõi.** Chỉ tùy biến qua các điểm mở rộng: `librechat.yaml`, `.env`, `docker-compose.override.yml`, MCP server, custom endpoint. Lý do: LibreChat viết bằng Node.js + MongoDB (JD ưu tiên Python + CSDL quan hệ), và dự án ra bản mới thường xuyên nên fork sâu sẽ rất khó nâng cấp.

**Checkpoint:** cuối mỗi giai đoạn phải (a) trả lời trôi chảy các *câu hỏi bản chất* mà không nhìn tài liệu, và (b) chạy được phần demo của giai đoạn đó.

---

## 1. Phân tích khoảng cách: JD, LibreChat và phần tự làm

> **Đối chiếu với LibreChat v0.8.9** (bản phát hành 17/11/2026, source đọc tại `librechat-src/`, cấu hình `version: 1.3.19`). Khi nâng cấp bản mới, rà lại bảng này.

| Yêu cầu JD | LibreChat có sẵn (v0.8.9) | Bạn tự xây / tự học | Giai đoạn |
|---|---|---|---|
| Triển khai nền tảng mã nguồn mở cho AI Agent | ✅ Toàn bộ nền tảng (MIT, Docker Compose / Helm) | Cài đặt, cấu hình, đọc source, xử lý lỗi, nâng cấp | GĐ0, GĐ4 |
| Tool calling, MCP | ✅ Agents, MCP client (stdio / Streamable HTTP / SSE), tool search / defer, sub-agent | **MCP server bằng Python**; tự viết agent loop để hiểu bản chất | GĐ1 |
| Kết nối dữ liệu nội bộ (nhân sự, văn bản, hồ sơ dự án) | ✅ Truyền danh tính xuống MCP: header `{{LIBRECHAT_USER_EMAIL}}`/`{{LIBRECHAT_USER_ID}}`, `{{LIBRECHAT_OPENID_ACCESS_TOKEN}}`, OAuth theo user, **OBO** | MCP server truy cập dữ liệu, **tự kiểm tra quyền dữ liệu** theo danh tính nhận được | GĐ1, GĐ2 |
| Quản lý ngữ cảnh, bộ nhớ, lập kế hoạch đa bước | ✅ User Memory (memory agent tự cập nhật), tóm tắt hội thoại (`summarization`), Agents | Hiểu cơ chế; tự cài trong agent service | GĐ1 |
| Human-in-the-loop cho tool | ✅ Chế độ duyệt tool theo agent (luôn hỏi / hỏi 1 lần mỗi chat / luôn cho phép) | Chọn tool nào bắt buộc duyệt; giải thích được vì sao | GĐ1, GĐ4 |
| Kho tri thức nội bộ (RAG, OCR) | ⚠️ "Chat với file" (rag_api, pgvector) theo file/agent; OCR: `mistral_ocr` (mặc định, cloud), **`custom_ocr`**, `document_parser` | Kho tri thức cấp tổ chức có **lọc quyền theo phòng ban**, hiệu lực văn bản, **OCR tiếng Việt on-prem** (có thể cắm lại vào LibreChat qua `custom_ocr`), eval | GĐ2 |
| Agent tự tích lũy kỹ năng, kho kinh nghiệm dùng chung | ✅ **Skills** (SKILL.md): CRUD, phiên bản, chia sẻ theo ACL, gắn vào agent, thư mục `skill/` dùng chung toàn hệ thống, **Skills management API**. ❌ Chưa có vòng đời tự rút kinh nghiệm → duyệt | Chỉ xây **pipeline kinh nghiệm**: rút bài học → đề xuất → duyệt → xuất bản qua Skills API; kho kinh nghiệm (episodic) | GĐ3 |
| Trợ lý thao tác trình duyệt / phần mềm | – | Playwright (MCP) – chỉ cấu hình | GĐ3 |
| Teams, WhatsApp | ⚠️ `channel-gateway` **chỉ hỗ trợ Slack**; ✅ có **Agents API** tương thích OpenAI (`/v1/chat/completions`, `/v1/events`, `/v1/models`) | channel-bridge Teams/WhatsApp bằng Python, gọi Agents API (dùng chung agent, MCP, quyền với web) | GĐ3 |
| Mini-app (so sánh văn bản, trích xuất scan, biên bản họp) | – | Tool/MCP hoặc agent chuyên biệt | GĐ3 |
| Xác thực, phân quyền | ✅ Local, OIDC (Entra ID), LDAP, SAML, passkey; role, group, chia sẻ Viewer/Editor/Owner | Ánh xạ danh tính → quyền dữ liệu trong MCP server (role LibreChat chỉ là quyền *tính năng*) | GĐ0, GĐ1, GĐ4 |
| Kiểm soát chi phí | ✅ Giao dịch token, balance (reserve, refill add/reset), dashboard admin | Cấu hình, **báo cáo chi phí theo phòng ban** (LibreChat không biết phòng ban), tối ưu | GĐ4 |
| Lưu vết dữ liệu | ⚠️ Lưu hội thoại, giao dịch token, audit admin (ví dụ thay đổi cấu hình MCP server – `packages/api/src/mcp/audit.ts`); trace qua Langfuse / OpenTelemetry | **Audit ở mức tool** (ai gọi tool nào, đọc dữ liệu gì) trong MCP server | GĐ4 |
| Mẫu prompt chuẩn, hướng dẫn phòng ban | ✅ Thư viện prompt, chia sẻ theo nhóm | Viết bộ prompt mẫu và tài liệu hướng dẫn | GĐ4, GĐ5 |
| Linux, Docker, reverse proxy, CI/CD | – | Vận hành cả stack trên server | GĐ4 |
| Có sản phẩm demo | – | Demo xuyên suốt (mục 2) | Mọi giai đoạn |

**Không tự xây lại** những thứ đã có: đăng nhập/SSO, role và chia sẻ, balance, thư viện prompt, memory, duyệt tool, lưu trữ skill, kênh Slack, tracing. Việc của bạn là cấu hình, hiểu cơ chế bên dưới và giải thích được.

**Lợi thế khi phỏng vấn:** tư duy backend (API, auth, tích hợp, logging) là thứ nhiều "AI engineer" thiếu. Teams và Bot Framework / Microsoft 365 Agents SDK hỗ trợ C# rất tốt, là điểm cộng khi tích hợp vào hệ sinh thái Microsoft.

---

## 2. Sản phẩm demo: "Trợ lý số nội bộ" trên nền LibreChat

**LibreChat làm vỏ** (giao diện, đăng nhập, agents, thư viện prompt, ngân sách). **Python làm lõi** (dữ liệu nội bộ, kho tri thức, kỹ năng, kênh chat, agent tự viết).

```
Người dùng (Web LibreChat / Teams / WhatsApp)
            │
      [Reverse proxy: Nginx/Caddy - TLS, timeout cho streaming]
            │
      [LibreChat]  ── Đăng nhập (local / Entra ID / LDAP), role & group, thư viện prompt, balance
         │  Agents
         ├─ MCP (Streamable HTTP) ─► [Python] hr-mcp        : dữ liệu nhân sự, phân quyền theo user
         ├─ MCP ─────────────────► [Python] knowledge-mcp : kho tri thức + lọc quyền + OCR tiếng Việt
         ├─ MCP ─────────────────► [Python] experience-mcp: kho kinh nghiệm + đề xuất skill
         │                              └─ (sau khi duyệt) ─► Skills management API của LibreChat
         ├─ MCP ─────────────────► Playwright MCP          : thao tác trình duyệt
         ├─ Skills (có sẵn)                                : skill đã duyệt, dùng chung toàn tổ chức
         └─ Custom endpoint ─────► [Python] agent-service  : agent loop tự viết (tương thích OpenAI API)

[Python] channel-bridge (Teams / WhatsApp) ─► Agents API của LibreChat (/v1/chat/completions)
[channel-gateway có sẵn]  (Slack)          ─► LibreChat
[PostgreSQL + pgvector] ◄── dữ liệu của các service Python (MongoDB chỉ dành cho LibreChat)
```

**Cách MCP server biết đang phục vụ ai:** LibreChat chèn danh tính user vào header (`{{LIBRECHAT_USER_EMAIL}}`, `{{LIBRECHAT_USER_ID}}`; `requestHeaders` còn có `{{LIBRECHAT_BODY_CONVERSATIONID}}`, `{{LIBRECHAT_AGENT_ID}}`), hoặc chuyển tiếp token OpenID của user (`{{LIBRECHAT_OPENID_ACCESS_TOKEN}}`), OAuth theo từng user, hay token **On-Behalf-Of** (`obo`) với Entra ID – v0.8.9 đã hỗ trợ cả ba. MCP server **tự kiểm tra quyền** dựa trên danh tính đó, không tin vào những gì model gửi lên.

| Mốc | Nội dung | Xong sau |
|---|---|---|
| M1 | LibreChat chạy bằng Docker, nối Claude, có đăng nhập, role, balance | GĐ0 |
| M2 | Agent loop tự viết; hr-mcp nối vào LibreChat có phân quyền theo user; agent-service làm custom endpoint | GĐ1 |
| M3 | knowledge-mcp: nạp PDF/scan, OCR on-prem, hybrid search, lọc quyền, trích dẫn, bộ eval | GĐ2 |
| M4 | experience-mcp (kinh nghiệm → đề xuất → duyệt → xuất bản qua Skills API); Playwright MCP; 2 mini-app; 1 kênh Teams hoặc WhatsApp qua Agents API | GĐ3 |
| M5 | Cả stack chạy trên Linux sau reverse proxy; CI; audit; dashboard chi phí; prompt mẫu | GĐ4 |
| M6 | README, sơ đồ, ADR, video demo, kịch bản demo | GĐ5 |

**Cấu trúc repo đề xuất:**

```
docs/            kế hoạch + notes/ (tài liệu ôn tập)
librechat/       librechat.yaml, .env.example, docker-compose.override.yml (KHÔNG chứa source fork)
librechat-src/   source LibreChat v0.8.9 (clone nông) – CHỈ ĐỌC để tham khảo, không sửa, không commit
services/        hr-mcp/, knowledge-mcp/, experience-mcp/, agent-service/, channel-bridge/
interview/       câu hỏi + đáp án, system design, STAR, kịch bản demo
backend/         code tham khảo viết dở từ trước (chỉ để đối chiếu)
```

---

## 3. Lộ trình chi tiết

### GĐ0: Dựng và hiểu LibreChat (Ngày 1–2)

**Mục tiêu:** LibreChat chạy được; hiểu kiến trúc và luồng một request, không chỉ "cài cho chạy".

#### Ngày 1: Môi trường và cài đặt
- Cài WSL2 (Ubuntu) và **làm việc trong Linux từ ngày đầu**; cài Docker, `uv`, Git, VS Code.
- Source LibreChat v0.8.9 đã có ở `librechat-src/` (đọc trước `CONTEXT.md` – bảng thuật ngữ của dự án, và `librechat.example.yaml`). Chạy bằng Docker Compose với **image ghim tag `v0.8.9`**, không dùng `latest`. Đọc `docker-compose.yml` và trả lời: có những service nào (api, mongodb, meilisearch, vectordb, rag_api…), mỗi service làm gì, nói chuyện với nhau qua cổng nào.
- Cấu hình `.env` và `librechat.yaml`: nối Claude, bật đăng nhập email, tạo user admin và user thường.
- Tự chấm điểm 1–5 cho từng dòng JD ở bảng mục 1 (cuối kế hoạch chấm lại).

#### Ngày 2: Cấu hình nâng cao và đọc source
- Role và quyền: tạo role riêng, bật/tắt quyền tạo/chia sẻ agent, prompt, MCP theo role; thử chia sẻ theo Viewer/Editor/Owner.
- Balance: bật giới hạn ngân sách, xem token được ghi vào đâu.
- Đăng nhập SSO: thử OIDC với Keycloak (chạy Docker) hoặc một tenant Entra ID miễn phí. Hiểu luồng OIDC: redirect, code, token, claims.
- Tạo một Agent trong giao diện, gắn file, chat thử.
- **Đọc source:** lần theo một tin nhắn từ lúc bấm gửi đến lúc gọi API của model: `api/server/routes/agents/chat.js` → `packages/api/src/agents` → `packages/api/src/mcp/MCPManager.ts`, `UserConnectionManager.ts` (chỗ gắn header theo user). Đọc log container khi có lỗi.
- Đọc nhanh Open WebUI và Dify (chỉ docs) để trả lời được: vì sao chọn LibreChat?

**✅ Checkpoint GĐ0**
1. Vẽ kiến trúc LibreChat: các service, dữ liệu nào nằm ở đâu.
2. Một tin nhắn đi qua những bước nào từ trình duyệt đến model và quay lại (streaming)?
3. Luồng đăng nhập OIDC diễn ra thế nào? Role trong LibreChat kiểm soát được gì?
4. So sánh LibreChat, Open WebUI, Dify: khi nào chọn cái nào?
5. Nâng cấp LibreChat lên bản mới mà không mất cấu hình thì làm thế nào?

---

### GĐ1: AI Agent từ gốc và MCP (Ngày 3–7)

**Mục tiêu:** hiểu bên dưới Agents của LibreChat đang làm gì; tự viết agent loop; viết MCP server Python nối vào LibreChat có phân quyền theo user.

#### Ngày 3: Tool calling và agent loop tự viết

Kiến thức cốt lõi:
- **Model không tự chạy gì cả.** Nó chỉ sinh khối JSON "muốn gọi tool X với tham số Y"; code của bạn thực thi rồi gửi kết quả lại.
- Vòng lặp: `user → LLM → tool_use → chạy tool → tool_result → LLM → … → end_turn`.
- **Tên, mô tả và schema của tool chính là prompt.**
- Tool lỗi thì trả lỗi có ý nghĩa (`is_error`) để model tự sửa; parallel tool calls trả về trong một message.

Nguồn: Anthropic docs *Tool use*; Anthropic Engineering *Writing effective tools for agents*.

Thực hành: **tự viết agent loop khoảng 50–80 dòng** bằng SDK thuần với 3 tool (thời gian, máy tính, danh bạ nhân viên giả trong Postgres). In từng bước ra để quan sát.

Thí nghiệm:
- Xóa mô tả tool hoặc đặt tên mơ hồ, xem model chọn sai.
- Cho tool ném exception: model có tự thử lại không?
- Không giới hạn số bước và cho tool luôn trả "thử lại": thấy vòng lặp vô hạn, hiểu vì sao cần `max_steps`.

#### Ngày 4: Mẫu thiết kế agent và lập kế hoạch đa bước

Kiến thức cốt lõi:
- **Workflow khác agent**: workflow có luồng do code quyết định; agent để model quyết định. Phần lớn bài toán doanh nghiệp chỉ cần workflow.
- Các mẫu: prompt chaining, routing, parallelization, orchestrator–workers, evaluator–optimizer.
- ReAct, plan-and-execute, re-planning khi gặp lỗi.
- Điều kiện dừng, giới hạn bước/ngân sách, **human-in-the-loop** cho hành động có tác dụng phụ.
- Sub-agent: dùng khi cần cô lập context.

Nguồn: Anthropic *Building effective agents* (đọc 2 lần); paper ReAct (Yao et al., 2022); Lilian Weng *LLM Powered Autonomous Agents*.

Thực hành: thêm tool `update_plan` (todo list) vào agent loop; chạy nhiệm vụ nhiều bước và quan sát. Sau đó tạo cùng nhiệm vụ bằng Agents của LibreChat và so sánh hành vi.

#### Ngày 5: Context engineering và bộ nhớ

Kiến thức cốt lõi:
- Context là tài nguyên khan hiếm: dài thì đắt, chậm, dễ "lạc" (context rot).
- **Ngắn hạn**: cửa sổ lịch sử, tóm tắt/nén (compaction), cắt bớt kết quả tool.
- **Dài hạn**: semantic (tri thức), episodic (sự kiện đã xảy ra), procedural (cách làm, tức skill).
- Working memory: scratchpad, todo, file ghi chú.
- Không sửa lịch sử giữa chừng (append-only) để tận dụng prompt cache.

Nguồn: Anthropic Engineering *Effective context engineering for AI agents*; paper MemGPT (Packer et al., 2023).

Thực hành:
- Thêm tóm tắt lịch sử khi vượt N token vào agent loop của bạn.
- Bật User Memory trong LibreChat, đọc docs và source để trả lời: nó lưu gì, lưu ở đâu, chèn vào context lúc nào?

#### Ngày 6: MCP và MCP server đầu tiên (hr-mcp)

Kiến thức cốt lõi:
- **Vấn đề MCP giải quyết**: N ứng dụng × M hệ thống = N×M tích hợp, chuẩn hóa thành N+M (giống LSP cho IDE).
- Kiến trúc Host / Client / Server; primitives: **Tools**, **Resources**, **Prompts** (thêm sampling, elicitation).
- JSON-RPC 2.0; transport **stdio** (local) và **Streamable HTTP** (remote).
- Bảo mật: OAuth cho server remote, tool poisoning, confused deputy, least privilege.
- MCP là lớp *phân phối và tái sử dụng* tool; bên dưới vẫn là tool calling.

Nguồn: `modelcontextprotocol.io` (Architecture, Specification: Tools, Transports, Authorization); MCP Python SDK; MCP Inspector; docs MCP của LibreChat.

Thực hành:
- Viết **hr-mcp** bằng Python (Streamable HTTP): `lookup_employee`, `get_leave_balance`.
- Nối vào LibreChat qua `librechat.yaml`, truyền danh tính user qua header (ví dụ `{{LIBRECHAT_USER_EMAIL}}`). Đọc thêm phần `obo` và `{{LIBRECHAT_OPENID_ACCESS_TOKEN}}` trong `librechat.example.yaml`: đây là bước nâng cấp từ "tin header" lên "kiểm token" khi có Entra ID.
- Thử chế độ duyệt tool (`docs/tool-approval-modes.md`) cho một tool có tác dụng phụ.
- **Phân quyền ở server**: nhân viên thường chỉ xem thông tin danh bạ; HR mới xem được số ngày phép của người khác.
- Debug bằng MCP Inspector và **đọc tận mắt các message JSON-RPC** (`initialize`, `tools/list`, `tools/call`).

Thí nghiệm: giả mạo email trong tham số tool (thay vì header) và xem server có bị lừa không. Từ đó hiểu vì sao danh tính phải đến từ nền tảng, không đến từ model.

#### Ngày 7: Agent service làm custom endpoint (M2)

- Bọc agent loop của bạn thành service Python có API tương thích OpenAI (`/v1/chat/completions`, có streaming), khai báo làm **custom endpoint** trong LibreChat.
- Agent service tự kết nối hr-mcp (bạn tự viết MCP client).
- So sánh 3 cách: Agents của LibreChat, agent tự viết, một framework (LangGraph hoặc tool runner của SDK). Mỗi cách làm hộ gì, che giấu gì, khi nào dùng.
- Viết note "Agent loop của tôi hoạt động thế nào" kèm sơ đồ.

Thí nghiệm: nạp 30–40 tool cùng lúc và đo độ chính xác chọn tool. Hiểu vì sao cần tool search, namespacing, thu gọn bộ tool.

**✅ Checkpoint GĐ1**
1. Mô tả chính xác một lượt tool calling, từng message một.
2. Khi nào dùng workflow, khi nào dùng agent? Ví dụ ở doanh nghiệp.
3. Agent lặp vô hạn hoặc gọi sai tool thì xử lý thế nào?
4. Các loại bộ nhớ của agent? Quản lý context dài ra sao?
5. MCP giải quyết vấn đề gì? Tools, resources, prompts khác nhau thế nào? stdio hay HTTP khi nào?
6. Làm sao đảm bảo agent không làm được nhiều hơn quyền của người đang ra lệnh? Danh tính user đi từ LibreChat đến MCP server thế nào?

---

### GĐ2: Kho tri thức, RAG và OCR (Ngày 8–11)

**Mục tiêu:** xây **knowledge-mcp**: kho tri thức cấp tổ chức, đo được chất lượng, có lọc quyền và OCR tiếng Việt chạy on-prem. Hiểu vì sao cần nó dù LibreChat đã có "chat với file".

#### Ngày 8: Embedding, chunking và pipeline nạp tài liệu

Kiến thức cốt lõi:
- Embedding và cosine similarity; tìm kiếm gần đúng (HNSW so với IVF); pgvector.
- Chọn embedding model đa ngôn ngữ cho tiếng Việt (ví dụ họ multilingual-e5, bge-m3), chạy local.
- Chunking: kích thước, overlap, chunk theo cấu trúc (Chương/Điều/Khoản), metadata (nguồn, trang, phòng ban, quyền, ngày hiệu lực), contextual retrieval, parent–child.
- Cập nhật tài liệu: phiên bản, xóa và nạp lại.

Nguồn: Anthropic *Introducing Contextual Retrieval*; paper RAG (Lewis et al., 2020); pgvector README.

Thực hành:
- **Đọc source service RAG của LibreChat** như tài liệu tham khảo: nó chunk thế nào, lưu gì vào pgvector, truy xuất bao nhiêu chunk.
- Viết pipeline nạp tài liệu của bạn: trích xuất, chunk, embed, lưu vào Postgres.

#### Ngày 9: Hybrid search, rerank và lọc quyền

Kiến thức cốt lõi:
- Vector search hỏng với mã số văn bản ("123/QĐ-TCT"), tên riêng, viết tắt; full-text hỏng với từ đồng nghĩa.
- Hybrid search và **Reciprocal Rank Fusion** (vì sao không cộng điểm trực tiếp).
- Reranker (cross-encoder) và bi-encoder; query rewriting; agentic RAG.
- **Lọc quyền ngay lúc truy xuất** (trong SQL), không lọc sau khi đưa vào prompt. Trích dẫn nguồn.

Thực hành: knowledge-mcp với tool `search_knowledge` (hybrid + RRF + lọc quyền theo phòng ban/role của user lấy từ header), nối vào LibreChat.

**Câu hỏi thiết kế cần tự trả lời:** "chat với file" của LibreChat khác kho tri thức tổ chức của bạn thế nào (phạm vi theo file/agent hay theo tổ chức, ai quản lý tài liệu, phân quyền theo phòng ban, OCR on-prem)?

#### Ngày 10: Xử lý tài liệu và OCR

Kiến thức cốt lõi:
- PDF có lớp text và PDF scan; tự động phát hiện trang cần OCR.
- Các lựa chọn: Tesseract (gói tiếng Việt), PaddleOCR, công cụ phân tích bố cục/bảng (Docling, Marker), mô hình có vision.
- Đánh đổi độ chính xác, chi phí, tốc độ, **quyền riêng tư**: OCR mặc định của LibreChat là Mistral OCR trên cloud, tài liệu nội bộ nhạy cảm có thể không được gửi ra ngoài.
- Trích xuất dữ liệu có cấu trúc từ scan: OCR, LLM với JSON schema, validate, người duyệt khi độ tin cậy thấp.

Thực hành: thêm OCR on-prem vào pipeline của knowledge-mcp; so sánh Tesseract với LLM vision trên cùng một bản scan tiếng Việt.

#### Ngày 11: Đánh giá RAG (M3)

Kiến thức cốt lõi:
- Golden set khoảng 30 câu hỏi kèm tài liệu đúng.
- Chỉ số truy xuất (recall@k, MRR); chỉ số câu trả lời (faithfulness, độ liên quan); LLM-as-judge và thiên lệch; RAGAS.

Thực hành: script eval chạy bằng một lệnh; cải tiến từng biến và ghi bảng trước/sau.

Thí nghiệm:
- Chunk 300 và 1500 ký tự: recall@5 thay đổi thế nào?
- Chỉ vector và hybrid, trên câu hỏi chứa số hiệu văn bản.
- **Prompt injection gián tiếp**: chèn "Bỏ qua mọi chỉ dẫn…" vào một tài liệu, xem agent trong LibreChat có bị lái không, rồi phòng chống.

**✅ Checkpoint GĐ2**
1. Vẽ pipeline RAG từ upload tài liệu đến câu trả lời có trích dẫn.
2. RAG trả lời sai: debug theo thứ tự nào?
3. Vì sao cần hybrid search? RRF hoạt động thế nào?
4. Lọc quyền đặt ở đâu? Vì sao không để LLM tự lọc?
5. Vì sao bạn tự xây knowledge-mcp thay vì chỉ dùng "chat với file" của LibreChat?
6. Khi nào dùng RAG, khi nào nhét cả tài liệu vào context, khi nào fine-tune?

---

### GĐ3: Agent tự tích lũy kỹ năng, tự động hóa và tích hợp (Ngày 12–15)

**Mục tiêu:** làm chủ điểm khác biệt nhất của JD và các kênh triển khai.

#### Ngày 12: Lý thuyết skill library và experience memory

Kiến thức cốt lõi:
- **Voyager** (Wang et al., 2023): agent tự viết kỹ năng, lưu thư viện, truy xuất cho nhiệm vụ mới.
- **Reflexion** (Shinn et al., 2023): tự đánh giá sau mỗi lần thử, ghi bài học bằng ngôn ngữ tự nhiên.
- **Generative Agents** (Park et al., 2023): memory stream, truy xuất theo độ gần đây, độ quan trọng, độ liên quan.
- **Agent Skills** (định dạng SKILL.md): *progressive disclosure*, agent chỉ thấy tên và mô tả, khi cần mới tải nội dung.
- Procedural (skill), episodic (kinh nghiệm), semantic (tài liệu).

Nguồn: Anthropic Engineering *Equipping agents for the real world with Agent Skills*; ba paper trên (abstract, sơ đồ, phương pháp).

Bài tập:
- **Đọc docs và source Skills + User Memory của LibreChat**: đã có gì, còn thiếu gì so với yêu cầu "tự tích lũy, quản lý tập trung, tái sử dụng toàn tổ chức".
- Thiết kế trên giấy **vòng đời một kỹ năng trong tổ chức**:

```
Thu thập (sau nhiệm vụ) → Phản tư (LLM rút bài học) → Đề xuất skill (bản nháp)
→ Duyệt (người phụ trách) → Xuất bản (v1) → Truy xuất khi có nhiệm vụ tương tự
→ Đo lường (số lần dùng, feedback, tỉ lệ thành công) → Cải tiến (v2) / Ngừng dùng
```

Câu hỏi quản trị: ai sở hữu skill, versioning, tránh "nhiễm độc bộ nhớ" (bài học sai lan ra toàn tổ chức), lọc thông tin cá nhân, phân quyền skill theo phòng ban.

#### Ngày 13: experience-mcp (M4a)
- **Không tự làm kho skill**: LibreChat v0.8.9 đã lưu, đánh phiên bản, chia sẻ và nạp skill theo progressive disclosure. Đọc `docs/skills-management-api.md` và `skill/README.md` trong `librechat-src/`.
- Tool của experience-mcp: `record_lesson` (ghi kinh nghiệm kèm embedding), `search_experiences`, `propose_skill` (tạo bản nháp trong DB của bạn, **chưa** đẩy lên LibreChat).
- Luồng duyệt: người phụ trách duyệt bản nháp → service gọi Skills management API (`POST /api/agents/v1/skills`, cập nhật bằng `expectedVersion`) → skill dùng được cho các agent được gắn.
- Ghi lại chủ sở hữu, phòng ban, tài liệu nguồn, ngày hết hạn ở phía bạn (Skills API không cho đặt owner/tenant).
- Trong agent-service: tự động bước reflection sau nhiệm vụ (dùng model rẻ, trả JSON) và truy xuất top-3 kinh nghiệm đầu nhiệm vụ.

Thí nghiệm: chạy cùng nhiệm vụ 3 lần (lần đầu chưa có kinh nghiệm), đo số bước, token, chất lượng.

#### Ngày 14: Thao tác trình duyệt và mini-app

Kiến thức cốt lõi:
- Playwright: selector, auto-wait, headless, trace viewer. Hai trường phái: DOM/accessibility tree và ảnh chụp màn hình (computer use).
- RPA và agent: RPA giòn khi giao diện đổi, agent linh hoạt nhưng không tất định.
- An toàn: xác nhận trước hành động không hoàn tác, sandbox, không để mật khẩu trong prompt.

Thực hành:
- Nối một Playwright MCP server vào LibreChat; cho agent đọc bảng và điền form trên một trang web nội bộ giả lập do bạn tự dựng.
- Mini-app (chọn 2): **so sánh văn bản** (diff + LLM tóm tắt thay đổi có ý nghĩa); **biên bản họp** (speech-to-text bằng faster-whisper/WhisperX, rồi LLM sinh tóm tắt, quyết định, việc cần làm). Đóng gói thành tool MCP hoặc agent riêng trong LibreChat, kèm prompt mẫu trong thư viện prompt.

#### Ngày 15: Kênh Teams / WhatsApp (M4b)

Kiến thức cốt lõi:
- **Teams**: Outgoing Webhook (HMAC, phải trả lời trong khoảng 5 giây), Bot (Bot Framework / Microsoft 365 Agents SDK, hỗ trợ C#), Incoming Webhook / Workflows để đẩy kết quả.
- **WhatsApp Cloud API**: verify token, chữ ký `X-Hub-Signature-256`, cửa sổ 24 giờ, message template, số test miễn phí.
- Vấn đề chung: **ánh xạ danh tính** kênh chat với user nội bộ và quyền của họ, xử lý bất đồng bộ khi agent chạy lâu hơn timeout, idempotency.
- Tunnel (ngrok, cloudflared) để test webhook local.

- Đọc `packages/channel-gateway/` (bản Slack có sẵn) làm mẫu: ánh xạ danh tính, render, xử lý bất đồng bộ.

Thực hành: channel-bridge cho **một** kênh, gọi **Agents API** của LibreChat (`/v1/chat/completions`, kiểm tra mount path và cách cấp API key) để dùng chung agent, MCP server và quyền như trên web. Tùy chọn: trỏ sang agent-service để so sánh.

**✅ Checkpoint GĐ3**
1. Thiết kế cơ chế để agent tự tích lũy kinh nghiệm và chia sẻ toàn tổ chức. Rủi ro và cách kiểm soát?
2. Skill, experience, tài liệu RAG khác nhau thế nào?
3. Progressive disclosure là gì, vì sao quan trọng khi có hàng trăm skill?
4. Tự động hóa trình duyệt bằng DOM hay vision? Làm sao cho ổn định?
5. Tích hợp agent vào Teams: các lựa chọn, timeout, danh tính, quyền?
6. Skills/Memory sẵn có của LibreChat (v0.8.9) đã làm được gì, còn thiếu gì (vòng đời rút kinh nghiệm, duyệt, hết hạn), bạn bổ sung ra sao?

---

### GĐ4: Vận hành production và quản trị (Ngày 16–17)

**Mục tiêu:** đưa cả stack ra môi trường thật: an toàn, đo được, kiểm soát được chi phí.

#### Ngày 16: Triển khai trên Linux

Kiến thức cốt lõi:
- Linux: quyền file, process, `systemd`, `journalctl`, `ss`, SSH, biến môi trường.
- Docker: image/layer, multi-stage build, volume, network, healthcheck; mở rộng compose của LibreChat bằng `docker-compose.override.yml` để thêm các service Python.
- Reverse proxy (Nginx/Caddy): TLS, định tuyến, **timeout và buffering cho streaming (SSE)**, giới hạn upload.
- CI/CD (GitHub Actions) cho các service Python: lint, test, build image, deploy.
- **Quy trình nâng cấp LibreChat**: đọc changelog, sao lưu MongoDB, đổi image, kiểm tra lại cấu hình.
- **Đọc source để sửa lỗi**: chọn một issue của LibreChat, tái hiện và lần đến dòng code liên quan.

Nguồn: MIT *The Missing Semester* (shell, scripting); Docker docs (Compose); docs triển khai của LibreChat.

Thực hành: deploy cả stack lên VPS rẻ (hoặc WSL), có domain/TLS và CI.

#### Ngày 17: Bảo mật, lưu vết, chi phí, chất lượng (M5)

Kiến thức cốt lõi:
- AuthN/AuthZ: OIDC với Entra ID, đồng bộ group; RBAC/ABAC; **quyền đi xuyên suốt** từ LibreChat qua MCP đến dữ liệu.
- **OWASP Top 10 for LLM Applications**: prompt injection, excessive agency, lộ thông tin nhạy cảm…
- Guardrails, che PII, danh sách hành động cần người duyệt.
- **Audit ở mức tool** trong MCP server: ai, lúc nào, tool nào, tham số gì, đọc tài liệu nào.
- Chi phí: prompt caching, thu gọn context, model nhỏ cho việc phụ, balance theo user, báo cáo theo phòng ban.
- Observability: trace từng bước (Langfuse, OpenTelemetry); eval hồi quy trong CI; feedback người dùng đưa vào bộ eval.
- Chủ quyền dữ liệu: model cloud hay on-prem.

Thực hành: audit log trong các MCP server; dashboard chi phí theo phòng ban; viết 5 prompt mẫu cho các phòng ban trong thư viện prompt kèm 1 trang hướng dẫn sử dụng.

**✅ Checkpoint GĐ4**
1. Triển khai cả hệ thống lên server Linux từ đầu: các bước và thành phần?
2. Prompt injection gián tiếp là gì? Phòng chống bằng những lớp nào?
3. Đảm bảo agent tuân thủ phân quyền khi truy cập dữ liệu nhân sự thế nào?
4. Chi phí LLM tăng gấp 3: điều tra và tối ưu ra sao?
5. Đo chất lượng agent thế nào? Đổi model thì biết có tốt hơn bằng cách nào?
6. Nâng cấp LibreChat bị lỗi sau khi lên bản mới: xử lý thế nào?

---

### GĐ5: Hoàn thiện demo và luyện phỏng vấn (Ngày 18–19, dự phòng Ngày 20–21)

#### Ngày 18: Đóng gói và tổng hợp (M6)
- README: vấn đề, sơ đồ kiến trúc, bảng "tính năng ↔ dòng JD", phần nào là LibreChat và **phần nào bạn tự xây**, cách chạy bằng 1 lệnh.
- ADR ngắn cho các lựa chọn lớn: vì sao LibreChat, vì sao không fork, vì sao MCP, vì sao tự xây kho tri thức, vì sao pgvector, vì sao hybrid search.
- Quay video demo 3–5 phút.
- Gom notes thành tài liệu ôn; tự soạn đáp án cho mọi câu hỏi checkpoint (1–2 phút mỗi câu).

#### Ngày 19: System design và phỏng vấn thử
- System design: *"Thiết kế nền tảng AI Agent nội bộ cho tập đoàn 5.000 nhân viên, dữ liệu nhạy cảm, tích hợp Teams."* Khung: làm rõ yêu cầu → quy mô → kiến trúc → đi sâu RAG, agent, quyền → bảo mật → chi phí → giám sát → lộ trình triển khai.
- Mock interview (bạn bè, hoặc AI đóng vai người phỏng vấn theo JD); ghi âm và nghe lại.
- Chạy kịch bản demo đúng thời gian; chuẩn bị câu hỏi ngược.

---

## 4. Chuẩn bị phỏng vấn

### 4.1 Câu chuyện của bạn
- **Giới thiệu 60 giây:** "Tôi là backend/web developer X năm (C#). Hơn 1 năm qua tôi dùng AI agent hằng ngày, và gần đây đã triển khai LibreChat làm nền tảng trợ lý nội bộ, tự xây các MCP server Python cho dữ liệu nhân sự, kho tri thức có OCR và phân quyền, thư viện kỹ năng tự tích lũy, và tích hợp Teams…"
- **Kinh nghiệm C#** chứng minh "nền tảng backend vững": thiết kế API, tích hợp hệ thống, auth, DB.
- **Kinh nghiệm dùng Claude/Copilot** thành insight: 2–3 câu chuyện cụ thể (agent sai ở đâu, bạn viết hướng dẫn/cấu hình MCP thế nào để sửa, bài học về context và tool).
- 3 câu chuyện **STAR**: tích hợp hệ thống khó, xử lý sự cố production, tự động hóa quy trình.

### 4.2 Câu hỏi nên chuẩn bị thêm
- "Vì sao chọn LibreChat? Có nhược điểm gì? Sao không tự xây hết hoặc dùng Dify?" (build vs buy, Node.js vs Python, chi phí bảo trì, nâng cấp)
- "Phần nào trong demo là bạn tự viết? Giải thích agent loop bên dưới." (đây là câu chắc chắn bị hỏi)
- "Phòng Nhân sự muốn tự động hóa; bạn làm việc với họ thế nào để chọn bài toán?" (khảo sát quy trình, đo tần suất/thời gian, chọn việc lặp lại, rủi ro thấp, dữ liệu sẵn; pilot rồi đo ROI rồi mở rộng)
- "Bài toán nào *không nên* dùng AI agent?"
- "Kể một lần agent của bạn hỏng và bạn sửa thế nào." (lấy từ các thí nghiệm "phá")
- "Model cloud hay on-prem cho dữ liệu nội bộ?"
- "Làm sao để phòng ban không rành công nghệ vẫn dùng hiệu quả?"

### 4.3 Kịch bản demo (5 phút)
1. Đăng nhập 2 user khác quyền trên LibreChat, hỏi cùng câu, thấy kết quả khác nhau (lọc quyền ở MCP server).
2. Hỏi câu nhiều bước, xem agent gọi các tool.
3. Upload bản scan tiếng Việt, OCR on-prem, trích xuất ra JSON.
4. Agent đề xuất skill mới, admin duyệt, user khác dùng được ngay.
5. Gọi agent từ Teams/WhatsApp.
6. Audit log ở mức tool và chi phí theo phòng ban.

### 4.4 Câu hỏi ngược gợi ý
- Công ty dùng model nào, cloud hay on-prem? Có ràng buộc dữ liệu không?
- Đã có nền tảng chat AI nội bộ chưa (LibreChat, Open WebUI, Dify…) hay sẽ xây từ đầu?
- Phòng ban nào là pilot đầu tiên? Đo thành công bằng chỉ số gì?

---

## 5. Tiêu chí "sẵn sàng phỏng vấn"

- [ ] Giải thích được kiến trúc và luồng request của LibreChat; đã nâng cấp nó ít nhất 1 lần
- [ ] Tự viết lại agent loop có tool calling từ trí nhớ
- [ ] Giải thích được luồng JSON-RPC của MCP; đã viết MCP server có phân quyền theo user
- [ ] Vẽ được pipeline RAG; có bảng số liệu eval trước/sau cải tiến
- [ ] Trình bày được thiết kế skill library và experience memory kèm cơ chế quản trị
- [ ] Cả stack chạy bằng `docker compose up` sau reverse proxy, có CI
- [ ] Nói rõ được phần nào là LibreChat, phần nào tự xây, và vì sao
- [ ] Trả lời được mọi câu hỏi checkpoint, mỗi câu 1–2 phút
- [ ] Đã mock interview và system design ít nhất 1 lần
- [ ] Chấm lại bảng tự đánh giá ở GĐ0: mọi dòng từ 3/5 trở lên

---

## 6. Nguồn học tổng hợp

| Chủ đề | Nguồn |
|---|---|
| LibreChat | `librechat.ai/docs` (Features, Configuration, MCP, Authentication, Token usage, OCR, Access control), repo GitHub `LibreChat-AI/LibreChat`, changelog |
| Agent | Anthropic *Building effective agents*; *Effective context engineering for AI agents*; *Writing effective tools for agents*; Lilian Weng *LLM Powered Autonomous Agents* |
| Paper agent | ReAct (2022), Reflexion (2023), Voyager (2023), Generative Agents (2023), MemGPT (2023) |
| Skills | Anthropic *Equipping agents for the real world with Agent Skills*; docs Agent Skills |
| MCP | `modelcontextprotocol.io` (spec), MCP Python SDK, MCP Inspector |
| RAG | Anthropic *Contextual Retrieval*; paper RAG (Lewis et al., 2020); pgvector README; RAGAS docs; source service RAG của LibreChat |
| OCR / tài liệu | Tesseract, PaddleOCR, Docling, PyMuPDF |
| Audio | faster-whisper, WhisperX, pyannote |
| Tự động hóa | Playwright docs; Playwright MCP; browser-use |
| So sánh nền tảng | Open WebUI, Dify, n8n, RAGFlow, LangGraph |
| Kênh | Microsoft Teams (Outgoing Webhook, Bot Framework / M365 Agents SDK); WhatsApp Cloud API docs |
| DevOps | MIT *The Missing Semester*; Docker docs; GitHub Actions docs |
| Bảo mật & vận hành | OWASP Top 10 for LLM Applications; Langfuse docs; OpenTelemetry |

> Mẹo: đọc xong mỗi nguồn, viết 5 dòng "điều quan trọng nhất tôi học được" và 1 câu hỏi phỏng vấn có thể bị hỏi từ nguồn đó.
