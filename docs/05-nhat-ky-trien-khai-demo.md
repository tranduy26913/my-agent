# Nhật ký triển khai demo (cập nhật 2026-11-24)

Mục tiêu: chạy demo nhỏ, không vận hành lâu dài. Chat dùng model local qua LibreChat, RAG dùng chung model đó, đưa ra internet bằng Cloudflare Tunnel.

## 1. Kiến trúc hiện tại

```
Người dùng ──https──► Cloudflare (tranduyai.id.vn) ──named tunnel "demo-ai"──► máy local
                                                        chat.tranduyai.id.vn → localhost:3080 (LibreChat)

LibreChat ──(endpoint LocalAI, tắt streaming)──► local-ai:8080 ──► qwen3-4b (GPU RTX 2060 Super)
    │
    └─ Agent + tool MCP ──► knowledge-mcp (host :8100) ──► agent-db (Postgres :5433, 110 chunk)
                                  └─ sinh câu trả lời RAG ──► local-ai (cùng qwen3-4b)

Đăng nhập (từ 2026-11-24, docs/06 giai đoạn 6): MỘT đường duy nhất là Zitadel (auth.tranduyai.id.vn → zitadel:8180,
DB `zitadel` nằm trong agent-db).
  LibreChat  ──OIDC──► Zitadel;  MCP gửi  Authorization: Bearer <access token của người đang chat>
  Portal     ──OIDC──► Zitadel;  BFF gửi  Authorization: Bearer <access token của người đang đăng nhập>
  FastAPI và knowledge-mcp: kiểm chữ ký RS256 + iss + aud (project id) rồi tra email trong bảng `employees`
  để lấy phòng ban và vai trò. Không còn bảng `users`, JWT HS256 tự phát, X-KB-Token, X-Portal-Token.
```

Chỉ một model chat nằm trong VRAM; model embedding `multilingual-e5-large` chạy CPU trong tiến trình backend.

## 2. Đã làm được

| Hạng mục | Trạng thái |
|---|---|
| Domain `tranduyai.id.vn` (Vietnix) → DNS Cloudflare | Active |
| Named tunnel `demo-ai`, route `chat.` → `localhost:3080` | Healthy, trả HTTP 200 |
| LibreChat đổi `DOMAIN_CLIENT`/`DOMAIN_SERVER` thành `https://chat.tranduyai.id.vn` | Xong |
| Tắt đăng ký tự do (`ALLOW_REGISTRATION=false`) | Xong, kiểm tra qua `/api/config` |
| 5 tài khoản persona SVT (binh.le, ha.pham, mai.ngo, duc.hoang, huy.do) | Xong, mật khẩu ở `librechat/persona-accounts.txt` (đã vào `.gitignore`) |
| LocalAI chạy GPU (ảnh `latest-gpu-nvidia-cuda-12`), model `qwen3-4b` Q4_K_M 2.9 GiB | Chạy, ~30–60 token/giây |
| Endpoint custom "LocalAI" trong `librechat/librechat.yaml` | Chat thường chạy ổn |
| Adapter model local cho RAG: `backend/app/llm/local.py`, `LLM_PROVIDER=local` | Xong, 33 test đạt |
| Agent trong LibreChat gọi `ask_knowledge` qua MCP, trả lời có trích dẫn | Chạy được (đã thử với binh.le) |

## 3. Quyết định đã chốt

- **Không dùng quick tunnel** cho chat: tài liệu Cloudflare ghi quick tunnel không hỗ trợ SSE; URL đổi mỗi lần chạy.
- **Một model duy nhất `qwen3-4b`** cho cả chat và tổng hợp RAG, vì máy không đủ RAM chạy nhiều model. Không nâng lên 8B, ưu tiên tốc độ phản hồi.
- **Tắt streaming** cho endpoint LocalAI (`addParams: disableStreaming: true`). Lý do: với streaming, LibreChat lưu tham số tool rỗng và không gọi MCP (lỗi chỉ hiện "Ran ask_knowledge"). LocalAI phát tool call đúng, nên nghi lỗi ở cách LibreChat xử lý stream; chưa chứng minh.
- **Chưa bật Cloudflare Zero Trust/Access** (tạm bỏ qua theo yêu cầu).
- Tài khoản mới sau này tạo bằng trang riêng của admin (chưa có), tạm dùng script `create-user`.

## 4. Đo đạc

- RAG trong `knowledge-mcp`: 5–7 giây (lần đo trực tiếp), 12.6 giây trong lần thử qua LibreChat.
- Tổng một câu hỏi qua Agent: khoảng 35 giây (hỏi lúc 14:51:30, có câu trả lời lúc 14:52:05 UTC).
- Lần gọi đầu sau khi khởi động rất chậm (khoảng 139 giây khi nạp embedding và model).
- VRAM khoảng 7.6/8 GB: rất sát giới hạn.

### 4.1 Đo RAM trước khi chọn Keycloak hay Zitadel (2026-11-23, giai đoạn 0 của `06-ke-hoach-zitadel.md`)

Máy có 15,9 GB RAM. `.wslconfig` đặt `memory=12GB`, `swap=8GB`. Số liệu đo trong lúc toàn bộ hệ thống đang chạy (7 container + `local-ai` + `knowledge-mcp`). Máy cũng đang mở Claude, Edge và ChatGPT, như lúc làm việc bình thường.

| Thời điểm | RAM khả dụng của máy | vmmem (VM của WSL) | python (knowledge-mcp) |
|---|---|---|---|
| Rảnh, chưa nạp model | 1,4 GB | 4,7 GB | 0,14 GB |
| **Câu hỏi đầu tiên, phải nạp model (đỉnh)** | **0,01 GB** | 5,3 GB | 1,65 GB |
| Ngay sau câu hỏi đầu | 3,9 GB | 3,6 GB | 0,37 GB đang nằm trong RAM (bộ nhớ đã cấp 1,9 GB) |
| Câu hỏi thứ hai, model đã nạp sẵn (đỉnh) | 2,1 GB | 3,8 GB | 1,55 GB |

- Container (`docker stats`, sau khi đã nạp model): LibreChat 360 MB, local-ai 920 MB (trọng số model nằm trên VRAM), rag_api 180 MB, mongodb 113 MB, meilisearch 100 MB, vectordb 47 MB, agent-db 36 MB. Tổng khoảng 1,75 GB.
- Bên trong VM (`free -m`): dùng 2,0 GB, cache 6,4 GB, khả dụng 9,5 GB. **VM giữ khoảng 6 GB cache mà không trả lại cho Windows.** Đây là nguyên nhân chính khiến máy thiếu RAM, chứ không phải các container.
- Commit charge khoảng 32/33 GB. Windows tự nới file `pagefile.sys` (đang cấp 18 GB, đỉnh đã dùng 9,6 GB).
- Các phần mềm ngoài hệ thống đang chiếm khoảng 4–5 GB: Claude khoảng 2,5 GB, Edge khoảng 1,8 GB, ChatGPT và CCleaner.
- VRAM: 7,1/8 GB.

**Kết luận:** chọn **Zitadel**.
- Lúc model đã nạp sẵn, máy còn 2,1 GB khả dụng. Keycloak dùng 0,5–1 GB sẽ kéo con số này xuống dưới ngưỡng 1,5 GB đã đặt.
- Lúc khởi động nguội, máy đã hết sạch RAM, kể cả khi chưa có Keycloak.

Có thể quay lại Keycloak nếu làm cả hai việc sau:
1. Giảm `.wslconfig` xuống `memory=8GB` và bật `autoMemoryReclaim=gradual` (mục `[experimental]`), để VM trả cache lại cho Windows.
2. Lúc demo thì tắt các phần mềm không cần.

Sau đó đo lại bằng đúng quy trình này.

**Đo lại sau khi giảm WSL** (cùng ngày; `.wslconfig`: `memory=8GB`, `swap=4GB`, `autoMemoryReclaim=gradual`):

| Thời điểm | Trước | Sau |
|---|---|---|
| Rảnh, chưa nạp model | 1,4 GB | **3,5 GB** |
| Câu hỏi đầu tiên, phải nạp model (đỉnh) | 0,01 GB | 0,11 GB (mất 150 giây) |
| Câu hỏi sau, model đã nạp sẵn (đỉnh) | 2,1 GB | 2,2 GB (trả lời trong 2–5 giây) |

- Giảm WSL chỉ giúp **lúc rảnh**. Hai mức đỉnh gần như không đổi, vì đỉnh đến từ việc nạp model: model embedding khoảng 1,7 GB trong python, cùng file model chat 2,9 GB đọc qua page cache của VM (vmmem lên tới 5,7 GB).
- `autoMemoryReclaim=gradual` trả RAM lại cho Windows từ từ, không kịp với một đỉnh kéo dài khoảng 2 phút.
- **Kết luận giữ nguyên: dùng Zitadel.** Lúc model đã nạp sẵn, máy còn 2,2 GB; trừ đi phần Keycloak thì còn 1,2–1,7 GB, sát hoặc dưới ngưỡng 1,5 GB. Muốn dùng Keycloak thì phải tắt các phần mềm khác lúc demo (giải phóng được khoảng 4–5 GB).

**Sự cố trong lúc đo:** sau khi restart WSL, backend bị `agent-db` từ chối mật khẩu của role `agent`, dù phía client không đổi gì. Lúc 12:30 vẫn đăng nhập được, nên mật khẩu lưu trong DB đã bị đổi trong khoảng 12:31–12:40. Chưa rõ ai đổi, vì Postgres không ghi log câu lệnh. Đã đặt lại bằng `ALTER ROLE agent PASSWORD ...` về giá trị trong `config.py`. Nếu gặp lại lỗi này: kiểm tra xem có session hoặc script nào khác chạy `ALTER ROLE` không.

### 4.2 Zitadel giai đoạn 1 đã chạy (2026-11-23)

- Service `zitadel` trong `librechat/docker-compose.override.yml`: ảnh `ghcr.io/zitadel/zitadel:v4.20.5`, cổng `127.0.0.1:8180`, DB `zitadel` nằm trong `agent-db` (user `zitadel` riêng, không đọc được DB `agent` của backend).
- **RAM: khoảng 79 MB** (`docker stats`, lúc rảnh, CPU ~1%), thấp hơn nhiều so với ước tính 512 MB; `mem_limit` vẫn để 512m. Máy còn khoảng 2,3 GB khả dụng sau khi bật, trước đó 2,8 GB. Chưa đo lúc đỉnh (nạp model).
- **Login V1, không có container `zitadel-login`:** đặt `ZITADEL_DEFAULTINSTANCE_FEATURES_LOGINV2_REQUIRED=false` (mặc định của v4 là `true`). Docs Zitadel nói ở lại Login V1 là cách được hỗ trợ ở v4. Kiểm: `/ui/login/loginname` trả 200, `/ui/v2/login/` trả 404 (đúng như mong đợi).
- **Healthcheck:** lệnh `zitadel ready` đọc `TLS.Enabled` từ cấu hình chứ không đọc cờ `--tlsMode`, nên phải thêm `ZITADEL_TLS_ENABLED=false`, nếu không nó gọi `https://localhost:8080` và báo "not ready" mãi.
- Kiểm bằng `curl -H "Host: auth.tranduyai.id.vn" http://127.0.0.1:8180/.well-known/openid-configuration`: `issuer` là `https://auth.tranduyai.id.vn`. Zitadel chọn instance theo header Host, nên vào thẳng `localhost:8180` bằng trình duyệt sẽ không được; cần route tunnel (hoặc dòng trong file hosts).
- Bí mật (`ZITADEL_MASTERKEY`, `ZITADEL_DB_PASSWORD`, `ZITADEL_ADMIN_PASSWORD`) nằm trong `librechat/.env`; PAT khởi tạo nằm ở `librechat/zitadel-bootstrap/bootstrap.pat` (đã `.gitignore`). **Sao lưu `ZITADEL_MASTERKEY` cùng DB `zitadel`.**
- **Việc còn lại của giai đoạn 1 (phải làm trên Cloudflare, tunnel chạy bằng token nên route cấu hình trên dashboard):** thêm Public hostname `auth.tranduyai.id.vn` → `HTTP://localhost:8180`, bật HTTP/2 origin; thêm Access policy cho `auth.tranduyai.id.vn/ui/console*`.

## 5. Vấn đề còn tồn tại

1. **Chậm cho demo**: nghi chế độ suy nghĩ của Qwen3 tốn nhiều token (chưa đo tách từng bước).
2. **Streaming đang tắt**, câu trả lời hiện một lần sau vài chục giây.
3. **`local-ai` đang ở chế độ debug** (`LOCALAI_LOG_LEVEL=debug`). Tạo lại container sẽ chạy lại tác vụ "gallery warm-up" khoảng 4 phút, ngốn CPU và khoảng 3.7 GB mạng; trong lúc đó request đầu bị chậm hoặc lỗi 500.
4. **`knowledge-mcp` và FastAPI đang chạy nền theo phiên làm việc**, không tự chạy lại khi khởi động máy.
5. **Qwen3-4B gọi tool chưa ổn định**: có lượt trả lời bằng kiến thức riêng, lẫn chữ Hán; chưa nhắc rõ trong mô tả Agent.
6. ~~`kb-admin` chưa dùng được~~ — đã xong: portal gọi `/api/kb` thật qua BFF (docs/07, docs/08).
7. Container `local-ai` được tạo bằng `docker run`, không nằm trong `docker-compose.yml`. Container cũ `local-ai-cpu-old` (bản CPU) còn ở trạng thái dừng.

## 6. Cách chạy lại sau khi khởi động máy

1. Bật Docker Desktop, rồi trong `librechat`: `docker compose up -d`. **Zitadel phải lên (healthy) trước LibreChat**; LibreChat tự thử lại nền nếu lên sớm hơn, nhưng nút "Đăng nhập SVT" chưa dùng được trong lúc đó.
2. Bật `local-ai` nếu chưa chạy (cần `--gpus all`, mạng `librechat_default`, bốn volume `/configuration`, `/data`, `/models`, `/backends`, cổng 8080).
3. Trong `backend`: `.\.venv\Scripts\python -m app.knowledge_mcp` (cổng 8100, `LLM_PROVIDER=local` trong `backend/.env`) và `.\.venv\Scripts\python -m uvicorn app.main:app --port 8000` (FastAPI cho portal). Hai tiến trình này cần `OIDC_ISSUER` và `OIDC_PROJECT_ID` trong `backend/.env`, thiếu thì mọi request bị từ chối. Portal: `npm run dev` trong `portal/` (cổng 3100).
4. Đảm bảo service `cloudflared` của tunnel `demo-ai` đang chạy.
5. **Sao lưu**: dump cả hai DB `agent` và `zitadel` của agent-db (`docker exec agent-db pg_dump ...`) **cùng với** `ZITADEL_MASTERKEY` (trong `librechat/.env`, cất ngoài repo). Có DB mà mất MASTERKEY thì không giải mã được dữ liệu Zitadel; có MASTERKEY mà mất DB thì mất hết tài khoản. Bản dump trước giai đoạn 6: `librechat/backups/agent-2026-11-24-before-stage6.sql` (đã `.gitignore`).
6. Sửa `librechat/.env` thì phải `docker compose up -d --force-recreate --no-deps api`; lệnh `up -d` thường không nạp lại biến môi trường.

## 7. Việc có thể làm tiếp

- Tắt chế độ suy nghĩ của Qwen3 để giảm độ trễ, rồi tắt debug của `local-ai`.
- Tìm cách bật lại streaming (đọc cơ chế chạy tool sớm trong `@librechat/agents`).
- Đưa `local-ai` vào `docker-compose.override.yml` và đặt `knowledge-mcp` chạy như service.
- Bật Cloudflare Access cho `chat.tranduyai.id.vn`; viết trang admin tạo tài khoản.
- Chạy eval RAG với model local và so sánh với Claude.
