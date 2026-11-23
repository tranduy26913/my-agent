# Tự động hóa trình duyệt, mini-app và kênh chat (GĐ3, ngày 14–15)

## 1. Tự động hóa trình duyệt

### Hai trường phái
| | DOM / accessibility tree | Vision (ảnh chụp màn hình, computer use) |
|---|---|---|
| Agent nhìn thấy | Cây phần tử có role, name, ref | Ảnh pixel |
| Thao tác | Click theo ref/selector, điền form | Click theo tọa độ |
| Ưu | Nhanh, rẻ, chính xác, ít token | Dùng được với mọi giao diện (canvas, app desktop, Citrix) |
| Nhược | Không dùng được khi không có DOM | Chậm, đắt, sai lệch tọa độ |

Playwright MCP mặc định dùng accessibility snapshot → nên ưu tiên.

### Playwright – điều phải nắm
- **Locator** theo vai trò và nhãn (`getByRole('button', {name: 'Gửi'})`, `getByLabel`) bền hơn CSS/XPath.
- **Auto-wait**: Playwright chờ phần tử sẵn sàng → không cần `sleep`.
- Headless cho server; **trace viewer** để xem lại từng bước khi lỗi.
- Phiên đăng nhập: lưu `storageState`; **không đưa mật khẩu vào prompt**.

### RPA và agent
- RPA: kịch bản cố định, tất định, rẻ khi chạy, **giòn** khi giao diện đổi.
- Agent: linh hoạt, tự xử lý biến thể, nhưng không tất định, đắt hơn.
- Thực tế tốt: agent *khám phá* và sinh kịch bản → kịch bản được duyệt chạy như RPA → agent chỉ can thiệp khi kịch bản lỗi.
- Nếu hệ thống có API → **dùng API**, trình duyệt là phương án cuối.

### An toàn
- Xác nhận người dùng trước hành động không hoàn tác (gửi, xóa, thanh toán, nộp).
- Danh sách domain được phép; sandbox/container riêng; tài khoản dịch vụ quyền tối thiểu.
- Nội dung trang web là **dữ liệu không tin cậy** (prompt injection qua web).

## 2. Mini-app

### So sánh văn bản
1. Trích text hai phiên bản, chuẩn hóa (khoảng trắng, NFC).
2. Diff có cấu trúc theo Điều/Khoản (căn theo số hiệu Điều, không theo dòng) → biết Điều nào thêm/xóa/sửa.
3. LLM tóm tắt **thay đổi có ý nghĩa** (số tiền, thời hạn, nghĩa vụ, phạt) và bỏ qua thay đổi chính tả/định dạng; mỗi nhận định trỏ về vị trí diff.
4. Tư liệu thử: `docs/03-mo-phong-cong-viec/tu-lieu/hop-dong-v1.md` và `hop-dong-v2.md`.

### Biên bản họp
1. Speech-to-text: faster-whisper (nhanh, CPU/GPU), WhisperX (thêm căn thời gian từng từ), pyannote (tách người nói).
2. LLM sinh: tóm tắt, **quyết định**, **việc cần làm (ai – việc – hạn)**, vấn đề còn mở; ra JSON theo schema rồi render.
3. Kiểm tra: việc cần làm phải có người phụ trách là người có mặt; hạn chót là ngày hợp lệ.
4. Tư liệu thử: `tu-lieu/transcript-hop-du-an.md` (bản transcript có sẵn, dùng khi chưa làm phần âm thanh).

## 3. Microsoft Teams

| Cách | Hướng | Đặc điểm |
|---|---|---|
| Outgoing Webhook | Teams → service của bạn khi @mention | HMAC xác thực; phải trả lời nhanh (khoảng 5 giây) → không hợp agent chạy lâu |
| Incoming Webhook / Workflows | Service → kênh Teams | Chỉ đẩy thông báo một chiều |
| Bot (Bot Framework / Microsoft 365 Agents SDK) | Hai chiều, chat 1-1, nhóm, proactive message | Đăng ký Azure Bot, có SSO với Entra ID; SDK hỗ trợ tốt C# và Python/JS |

Xử lý agent chạy lâu: nhận tin → trả "đang xử lý" ngay → chạy nền (queue) → gửi kết quả bằng **proactive message** (lưu conversation reference).

## 4. WhatsApp Cloud API
- Webhook verify: Meta gửi GET với `hub.mode`, `hub.verify_token`, `hub.challenge` → trả lại `challenge` nếu token khớp.
- Mỗi POST có header `X-Hub-Signature-256` = HMAC-SHA256(app secret, body thô) → xác thực trên **body thô**, trước khi parse JSON.
- **Cửa sổ 24 giờ**: chỉ nhắn tự do trong 24 giờ sau tin cuối của user; ngoài cửa sổ phải dùng message template đã duyệt.
- Trả `200` nhanh, xử lý bất đồng bộ; Meta gửi lại webhook nếu lỗi → cần **idempotency** theo message id.

## 5. Vấn đề chung của mọi kênh
| Vấn đề | Giải pháp |
|---|---|
| Ánh xạ danh tính (Teams AAD object id, số WhatsApp → user nội bộ) | Bảng liên kết; với WhatsApp cần bước xác minh (OTP qua email công ty) |
| Quyền | Sau khi ánh xạ, gọi agent-service với danh tính nội bộ → MCP server kiểm tra quyền như trên web |
| Timeout | Trả lời ngay, xử lý nền, gửi kết quả sau |
| Trùng lặp | Idempotency key = message id |
| Định dạng | Markdown giới hạn, độ dài tin nhắn, thẻ (Adaptive Card) |
| Dữ liệu nhạy cảm qua kênh ngoài | Chính sách: WhatsApp không trả lương/hồ sơ cá nhân |

## Câu hỏi tự kiểm
1. Vì sao xác thực chữ ký phải làm trên body thô?
2. Thiết kế luồng khi agent mất 40 giây trả lời mà Teams Outgoing Webhook chỉ chờ vài giây.
3. Khi nào bạn khuyên khách hàng dùng RPA truyền thống thay vì agent?

## Nguồn
- Playwright docs (Locators, Auto-waiting, Trace viewer); Playwright MCP.
- Microsoft Learn: Outgoing Webhooks, Microsoft 365 Agents SDK / Bot Framework, proactive messages.
- Meta: WhatsApp Cloud API (Webhooks, Messages, Templates).
- faster-whisper, WhisperX, pyannote.
