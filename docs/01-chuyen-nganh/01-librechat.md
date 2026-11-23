# LibreChat: kiến trúc, cấu hình, vận hành (GĐ0, GĐ4)

> Tài liệu định hướng để đọc docs và source cho đúng chỗ. Chi tiết cấu hình thay đổi theo phiên bản: **luôn đối chiếu với `librechat.ai/docs` và `librechat.example.yaml` của bản bạn đang chạy.**

## 1. LibreChat là gì, không là gì

- Là **nền tảng chat AI tự host** (MIT): giao diện, đăng nhập, đa model, Agents, MCP client, thư viện prompt, chia sẻ, ngân sách token.
- Không phải: kho tri thức cấp tổ chức, hệ thống workflow, công cụ RPA. Những phần đó bạn xây bằng Python và cắm vào qua MCP / custom endpoint.
- Viết bằng **Node.js (Express) + React**, dữ liệu chính ở **MongoDB**.

## 2. Các service trong Docker Compose

| Service | Vai trò | Dữ liệu |
|---|---|---|
| `api` (LibreChat) | Backend Express + phục vụ frontend React | Kết nối Mongo, Meili, RAG API |
| `mongodb` | CSDL chính | user, hội thoại, message, agent, prompt, giao dịch token, balance |
| `meilisearch` | Tìm kiếm full-text trong lịch sử hội thoại | index message |
| `vectordb` | PostgreSQL + pgvector | vector của file người dùng upload |
| `rag_api` | Service Python (FastAPI) cho "chat với file" | nhận file, chunk, embed, truy xuất |

Câu hỏi tự kiểm: nếu xóa volume `vectordb`, người dùng mất gì? Nếu xóa `meilisearch`, mất gì? (Gợi ý: một cái mất dữ liệu, một cái chỉ cần index lại.)

## 3. Ba file cấu hình và vai trò

| File | Chứa gì | Nguyên tắc |
|---|---|---|
| `.env` | Bí mật, khóa API, cờ tính năng, cấu hình đăng nhập | Không commit; có `.env.example` |
| `librechat.yaml` | Endpoint, custom endpoint, MCP servers, interface, balance, phân quyền giao diện | Commit được (không chứa bí mật – dùng `${ENV_VAR}`) |
| `docker-compose.override.yml` | Mount `librechat.yaml`, thêm service của bạn (hr-mcp, knowledge-mcp…) | Không sửa `docker-compose.yml` gốc → nâng cấp không conflict |

## 4. Luồng một tin nhắn (cần tự lần lại trong source)

```
Trình duyệt (React) ──POST──► api/ route chat/agents
   └─ middleware: xác thực JWT, kiểm tra quyền, kiểm tra balance
      └─ build context: lịch sử hội thoại (Mongo), system prompt, memory, file (gọi rag_api)
         └─ client của endpoint (Anthropic / OpenAI / custom) gọi API model, bật stream
            └─ nếu model yêu cầu tool: gọi MCP / tool nội bộ → đưa kết quả lại model
               └─ stream từng token về trình duyệt qua SSE
                  └─ lưu message, ghi giao dịch token, trừ balance
```

Cách đọc: bắt đầu từ route trong `api/server/routes/`, đi vào controller, rồi client trong `api/app/clients/` hoặc package agents. Đặt log tạm hoặc đọc `docker compose logs -f api` khi gửi tin.

## 5. Đăng nhập và phân quyền

- **Phương thức**: email/password local, OAuth/OIDC (Entra ID, Keycloak, Google…), LDAP, SAML.
- **Luồng OIDC (Authorization Code)**: trình duyệt → redirect sang IdP → user đăng nhập → IdP redirect về với `code` → server đổi `code` lấy `id_token` + `access_token` → đọc claims (email, name, groups) → tạo/khớp user nội bộ → phát session JWT.
- **Role** (USER, ADMIN và role tùy chỉnh) kiểm soát *tính năng*: được tạo/chia sẻ agent, prompt, dùng MCP, v.v.
- **Chia sẻ tài nguyên** (agent, prompt…) theo Viewer / Editor / Owner cho user/group.
- Điều role của LibreChat **không** làm: quyết định user được đọc *dữ liệu nghiệp vụ* nào. Đó là việc của MCP server (xem `03-mcp.md`).

## 6. Agents, MCP và custom endpoint trong LibreChat

- **Agent** = model + instructions + bộ tool (tool có sẵn, MCP tools, file search, code interpreter…).
- **MCP server** khai báo trong `librechat.yaml` (khóa `mcpServers`): loại `stdio`, `sse`, `streamable-http`; có thể đặt `headers` dùng placeholder thông tin user (ví dụ email/id của user đang chat) – kiểm tra tên placeholder đúng theo docs bản hiện tại.
- **Custom endpoint**: bất kỳ API tương thích OpenAI (`/v1/chat/completions`). Đây là cửa để cắm `agent-service` tự viết.

## 7. Ngân sách và token

- Mỗi lần gọi model sinh **giao dịch** (prompt tokens, completion tokens, model, user) trong Mongo.
- **Balance**: mỗi user có số dư token credit; hết thì bị chặn; có thể tự nạp định kỳ.
- Muốn báo cáo theo **phòng ban**: LibreChat không biết phòng ban → bạn join giao dịch với dữ liệu user (từ group/claims hoặc hr-mcp).

## 8. Nâng cấp không mất cấu hình

1. Đọc changelog/release notes, đặc biệt mục breaking change của `librechat.yaml` (trường `version`).
2. Sao lưu: `mongodump`, dump Postgres `vectordb`, các volume upload.
3. Đổi tag image (không dùng `latest` trong production) → `docker compose pull && docker compose up -d`.
4. Kiểm tra: đăng nhập, gửi tin, gọi MCP, agent, balance. Có checklist smoke test.
5. Rollback: tag image cũ + khôi phục backup nếu migration dữ liệu đã chạy.

## 9. So sánh nhanh với lựa chọn khác

| | LibreChat | Open WebUI | Dify |
|---|---|---|---|
| Điểm mạnh | Đa model, Agents + MCP, auth doanh nghiệp, balance | Dễ dùng, mạnh với model local (Ollama), có pipeline Python | Builder workflow kéo-thả, RAG tích hợp, app API |
| Ngôn ngữ | Node.js + MongoDB | Python (FastAPI) | Python + TS |
| Hợp khi | Cổng chat AI chung cho toàn công ty | Đội nhỏ, ưu tiên on-prem/local | Bài toán dạng workflow, người không code tự dựng |
| Giấy phép | MIT | Có điều khoản thương hiệu – đọc kỹ bản hiện tại | Giấy phép riêng dựa trên Apache 2.0 có điều kiện – đọc kỹ |

> Lưu ý giấy phép thay đổi theo thời gian; khi phỏng vấn nói "tôi đã đọc license bản X" thay vì khẳng định chung chung.

## 10. Hiểu lầm hay gặp

- "Có Agents rồi thì không cần tự viết agent loop" → sai khi phỏng vấn: bạn phải giải thích được bên dưới.
- "Role admin/user là đủ phân quyền dữ liệu" → sai: role là quyền tính năng, không phải quyền dữ liệu.
- "Chat với file = kho tri thức" → sai về phạm vi, người quản lý tài liệu, phân quyền, OCR on-prem.

## Nguồn
- `librechat.ai/docs`: Configuration (`.env`, `librechat.yaml`), Features (Agents, MCP, Memory, OCR), Authentication, Token usage/Balance, Deployment.
- Repo `danny-avila/LibreChat` (tổ chức `LibreChat-AI` tùy thời điểm): `docker-compose.yml`, `librechat.example.yaml`, `api/`.
