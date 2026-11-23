# MCP: Model Context Protocol (GĐ1, ngày 6–7)

## 1. Vấn đề MCP giải quyết

Không có chuẩn: N ứng dụng AI × M hệ thống = N×M bộ tích hợp. Có MCP: mỗi ứng dụng viết 1 client, mỗi hệ thống viết 1 server → N+M. Giống **LSP** cho IDE: một language server dùng được ở mọi editor.

MCP **không thay thế** tool calling. Nó là lớp *đóng gói và phân phối* tool/dữ liệu. Cuối cùng, tool của MCP server vẫn được host chuyển thành định nghĩa tool đưa cho model.

## 2. Kiến trúc

```
Host (LibreChat, Claude Desktop, agent-service của bạn)
 ├─ MCP Client #1 ──1:1── MCP Server hr-mcp        (Streamable HTTP)
 ├─ MCP Client #2 ──1:1── MCP Server knowledge-mcp (Streamable HTTP)
 └─ MCP Client #3 ──1:1── MCP Server playwright    (stdio)
```

- **Host**: ứng dụng có LLM, quyết định đưa gì cho model, xin phép người dùng.
- **Client**: bộ kết nối giữ một phiên với đúng một server.
- **Server**: cung cấp năng lực; không cần biết model nào đang dùng.

## 3. Primitives

| Primitive | Ai điều khiển | Dùng cho | Ví dụ |
|---|---|---|---|
| **Tools** | Model quyết định gọi | Hành động, truy vấn | `lookup_employee`, `search_knowledge` |
| **Resources** | Ứng dụng/người dùng chọn | Dữ liệu đọc, có URI | `policy://nghi-phep/2026` |
| **Prompts** | Người dùng chọn (slash command) | Mẫu prompt có tham số | "Soạn quyết định nghỉ phép" |
| Sampling (client) | Server xin host gọi LLM | Server cần suy luận mà không giữ API key | Tóm tắt tài liệu trong server |
| Elicitation (client) | Server xin hỏi thêm người dùng | Thiếu thông tin | "Bạn muốn nghỉ từ ngày nào?" |

## 4. Giao thức trên dây (cần đọc tận mắt bằng MCP Inspector)

JSON-RPC 2.0. Chuỗi tối thiểu:

```jsonc
// 1. Bắt tay
→ {"jsonrpc":"2.0","id":1,"method":"initialize",
   "params":{"protocolVersion":"<phiên bản>","capabilities":{},"clientInfo":{"name":"librechat","version":"x"}}}
← {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"...","capabilities":{"tools":{}},"serverInfo":{...}}}
→ {"jsonrpc":"2.0","method":"notifications/initialized"}          // notification: không có id

// 2. Liệt kê tool
→ {"jsonrpc":"2.0","id":2,"method":"tools/list"}
← {"result":{"tools":[{"name":"get_leave_balance","description":"...","inputSchema":{...}}]}}

// 3. Gọi tool
→ {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_leave_balance","arguments":{"employee_id":"NV012"}}}
← {"result":{"content":[{"type":"text","text":"Còn 7.5 ngày"}],"isError":false}}
```

Lưu ý: lỗi *nghiệp vụ* của tool trả trong `result` với `isError: true` (model đọc được và tự sửa). Lỗi *giao thức* (method không tồn tại, tham số sai định dạng) trả trong `error` của JSON-RPC.

## 5. Transport

| | stdio | Streamable HTTP |
|---|---|---|
| Cách chạy | Host khởi động server như tiến trình con | Server là dịch vụ web độc lập, một endpoint (vd `/mcp`) nhận POST, có thể trả JSON hoặc stream SSE |
| Hợp với | Công cụ local, dev, một người dùng | Dịch vụ dùng chung cho cả công ty, triển khai trong Docker |
| Xác thực | Kế thừa quyền tiến trình | Header/token, OAuth 2.1 theo spec Authorization |
| Lưu ý | Không in log ra stdout (làm hỏng giao thức) – log ra stderr | Phiên (`Mcp-Session-Id`), timeout reverse proxy, CORS |

SSE kiểu cũ (HTTP+SSE hai endpoint) đã được thay bằng Streamable HTTP; LibreChat vẫn hỗ trợ để tương thích.

## 6. Danh tính và phân quyền – phần quan trọng nhất khi phỏng vấn

**Nguyên tắc: danh tính đến từ nền tảng, không đến từ model.**

```
User đăng nhập LibreChat (OIDC) ─► LibreChat biết email/id
   ─► gọi MCP kèm header X-User-Email: {{placeholder}}   (hoặc token OAuth/OBO của user)
      ─► hr-mcp đọc header, tra role/phòng ban trong DB
         ─► kiểm tra quyền TRƯỚC khi truy vấn ─► ghi audit ─► trả kết quả
```

Sai lầm cần tránh: tool có tham số `requester_email` để model điền. Model có thể bị prompt injection điền email của giám đốc → **confused deputy**.

Mức độ tin cậy tăng dần:
1. Header tĩnh dùng chung (API key) – chỉ biết "là LibreChat gọi", không biết user nào.
2. Header chứa email user do LibreChat chèn + mạng nội bộ khép kín + shared secret giữa LibreChat và MCP server.
3. Token theo user (OAuth / On-Behalf-Of với Entra ID) – server tự xác minh chữ ký token.

Nói rõ trong demo bạn ở mức nào và rủi ro còn lại.

## 7. Rủi ro bảo mật của MCP

| Rủi ro | Mô tả | Giảm thiểu |
|---|---|---|
| Tool poisoning | Mô tả tool chứa chỉ dẫn ẩn | Chỉ dùng server tin cậy, review mô tả, ghim phiên bản |
| Rug pull | Server đổi mô tả/hành vi sau khi đã được duyệt | Ghim phiên bản, cảnh báo khi `tools/list` thay đổi |
| Confused deputy | Server quyền cao làm thay người không có quyền | Kiểm tra quyền theo danh tính user thật |
| Excessive agency | Một server làm quá nhiều việc | Least privilege, tách server đọc và ghi |
| Lộ dữ liệu qua kết quả tool | Trả nhiều hơn mức cần | Lọc cột, che PII theo quyền |
| Indirect injection qua dữ liệu | Tài liệu/email chứa chỉ dẫn | Đánh dấu nội dung là dữ liệu, HITL cho hành động ghi |

## Câu hỏi tự kiểm
1. MCP khác gì một REST API thông thường? Vì sao không để model gọi thẳng REST?
2. Khi nào một chức năng nên là Resource thay vì Tool?
3. Viết lại chuỗi JSON-RPC từ `initialize` đến `tools/call` không nhìn tài liệu.
4. Bạn sẽ chứng minh với đội bảo mật rằng hr-mcp không bị giả mạo danh tính như thế nào?

## Nguồn
- `modelcontextprotocol.io`: Introduction, Architecture, Specification (Lifecycle, Transports, Tools, Resources, Prompts, Authorization), Security Best Practices.
- MCP Python SDK (`mcp`, FastMCP), MCP Inspector.
- Docs MCP của LibreChat.
