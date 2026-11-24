# Vận hành production, bảo mật, lưu vết, chi phí (GĐ4, ngày 16–17)

## 1. Bản đồ triển khai

```
Internet ─► DNS ─► [Caddy/Nginx :443, TLS]
                     ├─ /            ─► librechat api :3080
                     └─ (nội bộ)     ─► không public các MCP server
Mạng docker nội bộ: librechat, mongodb, meilisearch, vectordb, rag_api,
                    hr-mcp, knowledge-mcp, experience-mcp, agent-service, postgres-app
Ngoài: channel-bridge (cần public cho webhook Teams/WhatsApp, đi qua proxy)
```

## 2. Linux tối thiểu phải thạo
| Việc | Lệnh |
|---|---|
| Xem tiến trình, cổng | `ps aux`, `ss -tulpn`, `top`/`htop` |
| Log dịch vụ | `journalctl -u <svc> -f`, `docker compose logs -f <svc>` |
| Dịch vụ | `systemctl status/restart/enable` |
| Quyền | `chmod`, `chown`, user không phải root chạy docker (nhóm `docker`) |
| Đĩa | `df -h`, `du -sh *`, `docker system df` |
| Mạng | `curl -v`, `dig`, `nc -zv host port` |

## 3. Docker
- Multi-stage build cho service Python: stage build cài phụ thuộc bằng `uv`, stage runtime gọn, user không phải root.
- `healthcheck` cho mỗi service; `depends_on: condition: service_healthy`.
- Volume có tên cho dữ liệu; **không bao giờ** `docker compose down -v` trên production.
- Ghim tag image; không dùng `latest`.

## 4. Reverse proxy cho streaming
- Tắt buffering cho SSE (Nginx: `proxy_buffering off;`), tăng `proxy_read_timeout` (agent có thể chạy vài phút).
- `client_max_body_size` cho upload tài liệu.
- Header `X-Forwarded-*` đúng để LibreChat tạo callback URL OIDC chính xác.

## 5. CI/CD cho service Python
`lint (ruff) → type check → unit test → eval hồi quy nhanh (golden set nhỏ) → build image → push registry → deploy (pull + up -d) → smoke test`.

## 6. Bảo mật theo OWASP Top 10 for LLM Applications (bản 2025)
| Rủi ro | Trong hệ thống của bạn | Kiểm soát |
|---|---|---|
| Prompt injection (trực tiếp/gián tiếp) | Tài liệu RAG, trang web, email | Phân định dữ liệu, HITL, least privilege, eval |
| Lộ thông tin nhạy cảm | Lương, hồ sơ nhân sự | Lọc quyền ở server, che PII, không log nội dung nhạy cảm thô |
| Chuỗi cung ứng | MCP server bên thứ ba, model | Ghim phiên bản, review, SBOM |
| Excessive agency | Agent có tool ghi | Tách tool đọc/ghi, xác nhận, giới hạn phạm vi |
| System prompt leakage | Prompt chứa bí mật | Không đặt bí mật/quyền trong prompt |
| Tiêu thụ không giới hạn | Vòng lặp agent, user lạm dụng | Balance, rate limit, max steps |

Lưu ý: tên và thứ tự các mục thay đổi theo phiên bản OWASP; đọc bản hiện hành.

## 7. Audit ở mức tool
Mỗi lần `tools/call` ghi một dòng:

```json
{"ts":"2026-11-20T09:15:02+07:00","trace_id":"...","user":"lan.nguyen@cty-a.example",
 "channel":"web","server":"hr-mcp","tool":"get_leave_balance",
 "args":{"employee_id":"NV012"},"decision":"allow","reason":"self",
 "records_returned":1,"latency_ms":42}
```

- Ghi cả **deny** (quan trọng hơn allow khi điều tra).
- Không ghi nội dung nhạy cảm vào log; ghi id bản ghi.
- Log append-only, lưu tách khỏi DB nghiệp vụ, có thời hạn lưu trữ theo chính sách.

## 8. Chi phí
**Điều tra khi chi phí tăng gấp 3**: (1) tăng ở user/phòng ban/agent nào? (2) tăng số request hay token mỗi request? (3) input hay output token? (4) model nào? (5) có vòng lặp agent bất thường, tài liệu RAG khổng lồ, file đính kèm lớn, cache hit rate giảm?

**Tối ưu**:
- Prompt caching (giữ prefix ổn định); thu gọn kết quả tool; giảm top-k RAG.
- Routing: model nhỏ cho phân loại, tóm tắt, phản tư; model lớn cho suy luận khó.
- Giới hạn `max_tokens`, max steps; balance theo user; báo cáo theo phòng ban hằng tuần.
- Batch API cho việc không cần thời gian thực (nạp tài liệu, contextual retrieval).

## 9. Observability và chất lượng
- **Trace**: mỗi yêu cầu một trace, mỗi lần gọi LLM/tool là một span (input, output, token, độ trễ, lỗi). Langfuse hoặc OpenTelemetry.
- **Eval hồi quy**: golden set chạy trong CI khi đổi prompt/model/chunking; ngưỡng không được giảm.
- **Feedback**: nút 👍/👎 → đưa ca 👎 vào hàng đợi xem xét → bổ sung golden set.
- Đổi model: chạy cùng golden set, so điểm + chi phí + độ trễ; shadow test trên traffic thật trước khi chuyển.

## 10. Chủ quyền dữ liệu: cloud hay on-prem
| | Model cloud (API) | On-prem (vLLM, Ollama…) |
|---|---|---|
| Chất lượng | Cao nhất | Thấp hơn, đang thu hẹp khoảng cách |
| Chi phí | Theo token | Đầu tư GPU + vận hành |
| Dữ liệu | Rời hạ tầng (xem điều khoản lưu trữ, vùng dữ liệu) | Ở lại nội bộ |
| Gợi ý | Phân loại dữ liệu: công khai/nội bộ dùng cloud; mật (lương, hồ sơ) dùng on-prem hoặc chỉ trả dữ liệu đã lọc | |

## Câu hỏi tự kiểm
1. Liệt kê theo thứ tự các bước dựng cả stack trên một VPS trắng.
2. Một user báo "agent trả lời bị cắt sau 60 giây". Bạn nghi ngờ thành phần nào trước?
3. Vì sao audit phải nằm ở MCP server chứ không chỉ ở LibreChat?

## Nguồn
- MIT *The Missing Semester*; Docker docs (Compose, healthcheck, multi-stage); Nginx/Caddy docs.
- OWASP *Top 10 for LLM Applications*; Langfuse docs; OpenTelemetry GenAI semantic conventions.
