# ADR-005: Dịch vụ OCR dùng chung, engine thay được

- Trạng thái: **Đang triển khai** (engine mặc định đã đổi sang `paddleocr_vl` ngày 2026-11-24; `unlimited` không chạy được trên máy demo, không đủ VRAM) (đề xuất 2026-11-23, cập nhật cùng ngày sau khi làm xong giai đoạn 1–3 với Tesseract; chưa có engine `unlimited`)
- Liên quan: ADR-001 (phân quyền tài liệu), ADR-004 (Portal + Chat, một nghiệp vụ hai cách gọi), `docs/01-chuyen-nganh/04-rag-ocr-eval.md` mục 7, `docs/06-ke-hoach-zitadel.md`, `data/scan/ground-truth.md`
- Báo cáo đo: `data/eval/reports/2026-11-23-ocr.md` (sau tiền xử lý) và `2026-11-23-ocr-baseline-khong-tien-xu-ly.md` (trước)

## Bối cảnh

1. Backend **đã có OCR** nhưng nằm lẫn trong pipeline nạp tài liệu: `app/rag/ingest.py` (`extract_pages`, `ocr_image`) phát hiện PDF không có lớp text rồi chạy Tesseract (`vie+eng`, render 250 DPI). Chưa có cách gọi OCR riêng, ngoài việc nạp vào kho.
2. Cần một "tool OCR" cho người dùng: ADR-004 dự kiến màn `/tools/*` trên portal, và nghiệp vụ trích xuất phiếu (giấy đề nghị thanh toán công tác phí) cần OCR rồi kiểm tra theo quy định.
3. Có ứng viên engine mới là `baidu/Unlimited-OCR` (Unlimited-OCR-2, MIT, chạy qua SGLang với API tương thích OpenAI). Hiện biết về nó:
   - README không nêu hỗ trợ tiếng Việt, hai bài báo cũng không nêu ngôn ngữ nào (chỉ có thẻ `multilingual` trên Hugging Face). **Chưa kiểm chứng.**
   - Chỉ được thử trên A800-80GB, không nêu VRAM tối thiểu.
   - Không đọc PDF trực tiếp, phải đổi PDF thành ảnh trước.
4. Máy demo là RTX 2060 Super 8 GB, VRAM đã dùng khoảng 7.6/8 GB cho `qwen3-4b` (nhật ký `docs/05`, mục 4). Không có chỗ cho một model OCR thứ hai trên cùng GPU.
5. Lúc đề xuất, backend chưa có ứng dụng FastAPI. Nay `app/main.py` đã có (dùng chung với `/api/kb` do session khác thêm vào). Một session khác đang sửa `ingest.py` (ghi chú đầu `docs/06`).

## Quyết định

### 1. OCR là một service riêng ở tầng nghiệp vụ, REST là cách gọi đầu tiên
- Logic nằm trong package mới `app/ocr/` (`service.py`). Router `app/api/ocr.py` chỉ nhận request, kiểm tra quyền, gọi service rồi ghi vết.
- Theo ADR-004: nếu sau này cần gọi từ chat thì thêm một MCP server mỏng gọi cùng service, **không viết lại nghiệp vụ**. Chưa làm MCP, vì LibreChat chưa có cách chuyển file upload sang MCP tool một cách gọn.
- **Không sửa `ingest.py` lúc này.** Package mới đứng độc lập; khi session đang sửa `ingest.py` xong, đổi `ingest.py` sang gọi `app/ocr` để chỉ còn một bản logic OCR.

### 2. Engine OCR thay được qua một giao diện
Theo mẫu đã dùng cho `llm/` và `get_embedder()` (`app/ocr/engines/`, đăng ký trong dict `ENGINES`):

| Engine | Vai trò | Trạng thái |
|---|---|---|
| `tesseract` | **Dự phòng** (và mặc định khi chưa cấu hình engine khác). CPU, miễn phí. Có tiền xử lý ảnh (mục 3) và gợi ý bố cục `layout="rows"` cho biểu mẫu có bảng. Chỉ "sẵn sàng" khi có cả chương trình lẫn gói ngôn ngữ `vie` và `eng` | Đã làm, đã cài và chạy thật |
| `paddleocr_vl` | **Mặc định trên máy demo (2026-11-24).** PaddleOCR-VL-1.6 (0,9B, Apache-2.0) qua server nhỏ `ocr-engine/server/paddle_vl_server.py` (container `svt-ocr-paddle`, `127.0.0.1:10001`, `OCR_PADDLEVL_URL`). Vừa card 8 GB (1,7 GiB VRAM), 16–25 giây một trang. Backend cắt trang ở khung bảng (`app/ocr/layout.py`) để mỗi dòng bảng nằm trên một dòng chữ | Đã làm, đã chạy thật |
| `unlimited` | Client `httpx` gọi SGLang qua `/v1/chat/completions` (ảnh base64). Địa chỉ cấu hình bằng `OCR_SGLANG_URL`; không chạy chung GPU với `qwen3-4b` | **Client đã viết và test với server giả; server SGLang KHÔNG chạy được trên RTX 2060 Super 8 GB (2026-11-24): trọng số chiếm hết VRAM, không còn chỗ cho KV cache.** Xem `ocr-engine/README.md` |
| `fake` | Trả văn bản cố định, dùng trong test; không đăng ký trong `ENGINES` mặc định | Đã làm |

Chọn engine qua `OCR_ENGINE` (mặc định) và tham số `engine` của từng request. Tên engine sai trả 400; engine chưa sẵn sàng trả 503. Engine chỉ bị kiểm tra khi gặp trang **cần** OCR, nên PDF có lớp text vẫn đọc được dù engine đang tắt.

`recognize(image, *, layout=None)`: `layout="rows"` yêu cầu giữ mỗi dòng bảng trên một dòng văn bản (Tesseract dùng `--psm 6`); engine không hỗ trợ thì bỏ qua gợi ý. Chỉ trích xuất phiếu dùng gợi ý này; văn bản thường giữ chế độ mặc định vì chế độ `rows` làm WER xấu hơn (8,0% so với 6,5%).

### 3. Engine mặc định chọn theo số đo, không theo giới thiệu
- `app/ocr/eval.py` đo **CER/WER** trên `data/scan/` với đáp án `ground-truth.md`; chạy bằng `python -m app.ocr.eval [--engines a,b]`. Với phiếu (đáp án là JSON) đo tỉ lệ trường tìm thấy trong văn bản OCR. Bản OCR thô lưu ở `data/eval/reports/ocr-raw/`.
- Chỉ đổi engine mặc định sang `unlimited` khi CER tiếng Việt (đặc biệt vùng có dấu và vùng con dấu đỏ đè chữ ký) tốt hơn Tesseract có ý nghĩa **và** có chỗ chạy GPU (xem mục 6).

**Kết quả đo Tesseract 5.4 (gói `tessdata_best` tiếng Việt), 2026-11-23:**

| Phép đo | Không xử lý | Có tiền xử lý |
|---|---|---|
| SVT-TB-018 PNG: CER / WER | 3,8% / 6,5% | 3,9% / 6,5% |
| SVT-TB-018 PDF scan: CER / WER | 4,4% / 8,5% | 4,1% / 7,5% |
| Số tiền từng khoản trong bảng phiếu (NV017, NV018) | 0/4 và 1/5 | **4/4 và 5/5** |
| Trường đúng NV017 / NV018 | 8/12 và 9/13 | 11/12 và 13/13 |
| Thời gian mỗi phiếu | khoảng 2,5 giây | khoảng 1,4 giây |

**Tiền xử lý** (`app/ocr/preprocess.py`, bật bằng `OCR_PREPROCESS`, mặc định bật): khử nhiễu hạt (lọc trung vị) → nhị phân Otsu → xóa đường kẻ bảng (đoạn mực thẳng liên tục dài hơn 4% bề rộng ảnh). Chỉ dùng numpy + Pillow. Đã thử 6 biến thể; xóa đường kẻ là yếu tố quyết định, khử nhiễu hay đổi `--psm` riêng lẻ không giúp. Tiền xử lý nằm **trong engine Tesseract**, không ở service, vì engine hiểu bố cục (như Unlimited-OCR) cần ảnh gốc.

**Giới hạn của số đo:** chỉ 1 văn bản và 2 phiếu, đều là ảnh giả lập sạch. Chưa có ảnh chụp thật (nghiêng, bóng, mờ). Phép xóa đường kẻ có thể xóa nhầm gạch chân hoặc chữ đậm rất to; mẫu hiện có chưa gặp ca đó. Chưa có số đo cho `unlimited`.

### 4. Giao diện REST (tiền tố `/api/ocr`)

| Method | Đường dẫn | Việc làm | Giai đoạn | Trạng thái |
|---|---|---|---|---|
| GET | `/engines` | Liệt kê engine và tình trạng | 1 | Đã làm |
| POST | `/recognize` | Upload ảnh/PDF (multipart), chạy đồng bộ với giới hạn trang nhỏ; trả từng trang kèm nguồn `text-layer` hoặc `ocr` | 1 | Đã làm |
| POST | `/jobs` | Như trên nhưng bất đồng bộ, trả `202` kèm `job_id` và header `Location` | 2 | Đã làm |
| GET | `/jobs/{id}` | Trạng thái, tiến độ (`pages_done/pages_total`) và kết quả | 2 | Đã làm |
| GET | `/jobs` | Lịch sử job của chính người gọi (không kèm văn bản) | 2 | Đã làm |
| DELETE | `/jobs/{id}` | Xóa job và kết quả; job đang chạy thì worker tự dừng | 2 | Đã làm |
| GET | `/schemas` | Danh sách schema trích xuất | 3 | Đã làm |
| POST | `/extract` | OCR rồi trích xuất JSON theo `schema_id`, trả `findings` và cờ `needs_review`. **Đồng bộ** | 3 | Đã làm |
| GET | `/jobs/{id}/events` | SSE tiến độ | sau | Chưa làm (client phải poll) |

Dùng chung với `/api/kb`: `GET /healthz`, `GET /readyz` (đã có). `GET /api/me` chưa làm: với JWT cũ bảng `users` không có email nên chưa nối được sang `employees`; chờ phương án đăng nhập mới.

### 5. Dữ liệu, quyền và ghi vết
- **Xác thực (cập nhật 2026-11-24):** mọi endpoint (trừ `/healthz`, `/readyz`) cần token Zitadel của nhân viên đang hoạt động, qua `get_ocr_user` trong `app/api/deps.py` (đổi Principal thành `UserInfo`). Không còn nhận JWT HS256 cũ. `ocr_jobs.user_id`, `audit_logs.user_id` và `usage_logs.user_id` của OCR ghi **employees.id** (cột `ocr_jobs.user_id` vốn là Integer không khoá ngoại, nên không cần migration; bảng lúc chuyển đang rỗng). Audit kèm `actor` = email. Vai trò `admin` lấy từ `employees.roles`.
- **Kết quả OCR thuộc về người gọi.** Job chỉ người tạo xem được; người khác nhận **404** (cố ý không phân biệt "không tồn tại" với "không phải của bạn"). Admin xem được job người khác nhưng phải ghi audit `ocr_job_view` **trước** khi trả nội dung (ghi lỗi thì không trả: fail closed, theo mẫu `kb_view_classified` của ADR-004). Admin không xóa hộ được. Chủ job xem thì không ghi `ocr_job_view`.
- **Không lưu file gốc và không lưu tên file.** Chỉ lưu văn bản kết quả và metadata (engine, loại, số trang, thời gian, dung lượng). File gốc chỉ nằm trong RAM của tiến trình lúc chờ/xử lý. Job hết hạn sau `OCR_JOB_TTL_DAYS` (mặc định 7 ngày) và bị dọn lười biếng mỗi lần tạo job mới.
- **Không tự đưa vào kho tri thức.** Việc đưa kết quả vào kho thuộc `/api/kb` và phải theo ADR-001 (phạm vi truy cập, phòng ban) cùng bước làm sạch prompt injection của P2. Văn bản OCR là dữ liệu không đáng tin.
- **Ghi vết** (không chứa tên file, nội dung văn bản hay số tiền):

| Sự kiện `AuditLog` | Khi nào |
|---|---|
| `ocr_run` | `/recognize` thành công; job xong (thêm `async: true`, `job_id`) |
| `ocr_job_failed` | job thất bại |
| `ocr_job_view` | admin xem job của người khác |
| `ocr_extract` | `/extract` thành công (số lỗi, số cảnh báo, `needs_review`, model) |

  `UsageLog` ghi `purpose = "ocr"` hoặc `"ocr-extract"`; model cục bộ (`local:`) tính chi phí 0 như quy ước trong `observability.py`. Lỗi đầu vào bị từ chối thì **không** ghi vết "đã chạy".

### 6. Hạ tầng cho engine `unlimited` (chưa làm)
- Chạy ở venv Python 3.10 riêng (wheel SGLang tùy biến của repo), đặt trong thư mục `ocr-engine/` ở gốc dự án (README + script chạy), tách khỏi `backend/` như `librechat/`. Không trộn dependency với backend.
- **Không chạy chung GPU với `qwen3-4b` trên máy demo.** `OCR_SGLANG_URL` trỏ tới máy GPU khác hoặc dịch vụ bên ngoài. Nếu dùng dịch vụ bên ngoài (Hugging Face Spaces, TextMind của Baidu) thì dữ liệu rời hạ tầng: **chỉ được dùng cho tài liệu công khai/thử nghiệm**, không dùng cho tài liệu `han-che` hoặc Mật, theo hướng on-prem của P3.
- Backend phải chạy được khi engine `unlimited` tắt: `/engines` báo `unavailable`, request chọn engine đó nhận 503, request mặc định không bị ảnh hưởng (cơ chế này đã có và đã test với engine giả).

### 7. Giới hạn đầu vào và vận hành
Tất cả cấu hình được trong `app/config.py`:

| | Request đồng bộ | Job bất đồng bộ |
|---|---|---|
| Dung lượng | `OCR_MAX_MB` = 20 | `OCR_JOB_MAX_MB` = 50 |
| Số trang mỗi lần | `OCR_MAX_PAGES` = 10 | `OCR_JOB_MAX_PAGES` = 100 |
| Hạn mức | | tối đa 3 job đang chờ/chạy mỗi người, 20 toàn hệ thống (429 khi vượt) |

- Chặn ảnh/trang quá lớn (`OCR_MAX_PIXELS` = 60 triệu điểm ảnh); render PDF 250 DPI (`OCR_RENDER_DPI`).
- Xác định loại file theo **nội dung** (chữ ký đầu file), không tin đuôi file hay `Content-Type`. Chỉ nhận PNG, JPEG, TIFF, BMP và PDF; từ chối PDF có mật khẩu, PDF/ảnh hỏng.
- Mỗi engine chỉ chạy `OCR_MAX_CONCURRENCY` (mặc định 1) lượt OCR cùng lúc. Job chạy bằng `ThreadPoolExecutor` trong tiến trình (`OCR_JOB_WORKERS` = 2). Muốn nhiều máy thì thay hàm `_submit` bằng hàng đợi ngoài; phần còn lại giữ nguyên.
- **Job mất khi máy chủ khởi động lại** (file gốc chỉ ở RAM). Lúc khởi động, job đang chờ/chạy được đánh dấu `failed` để người dùng gửi lại. Hàng đợi nằm trong RAM của một tiến trình, nên chạy nhiều tiến trình uvicorn thì mỗi tiến trình có hàng đợi riêng (giới hạn toàn hệ thống vẫn đếm theo DB).
- Bảng `ocr_jobs` do ứng dụng tự tạo lúc khởi động (`checkfirst`, chạy ở luồng nền để DB tắt không chặn API).

### 8. Trích xuất có cấu trúc
**Luồng:** OCR (`layout="rows"`) → LLM chép ra JSON (đầu ra bị ép đúng schema, LocalAI dựng grammar) → chuẩn hóa → đối chiếu với văn bản OCR → kiểm tra số học và quy định → `findings` + `needs_review`. Code ở `app/ocr/extract.py` và `app/ocr/schemas/` (mỗi loại tài liệu là một module; thêm loại mới = thêm module và một dòng trong sổ đăng ký).

**Phân vai (nguyên tắc chính):**
- LLM **chỉ chép** dữ liệu theo schema; không phân loại khoản chi, không tính tổng, không phán vi phạm. LLM dùng theo `LLM_PROVIDER` (`local` = qwen3-4b, mặc định demo; `claude` = dùng model nhỏ; `fake` không hỗ trợ). Văn bản OCR đặt trong thẻ `<ocr>`, thẻ trong văn bản bị vô hiệu hóa, system prompt nói rõ đó là dữ liệu chứ không phải chỉ dẫn.
- Mọi phần còn lại là **mã tất định**: chuẩn hóa mã nhân viên (`NVO17` → `NV017`), phân loại khoản chi bằng từ khóa, đối chiếu từng số tiền/ngày/mã với văn bản OCR (giá trị không có trong OCR thì cảnh báo, chống model bịa), kiểm tra tổng và số dư, áp quy định.
- **Không tin LLM với cột hóa đơn.** Thử nghiệm thật cho thấy khi OCR làm mất cột "HĐ", qwen3-4b đoán bừa (gán "Không" cho cả vé máy bay và khách sạn, sinh 3 lỗi `thieu_hoa_don` giả). Cột này được đọc lại từ chính dòng OCR chứa số tiền của khoản đó; không đọc được thì để trống và báo **một** cảnh báo gộp `hoa_don_khong_doc_duoc`. Giá trị model đưa ra chỉ giữ ở `hoa_don_llm` để đối chiếu.
- Chỉ kết luận `needs_review` (true khi có `error` hoặc `warning`); **không bao giờ "duyệt chi"**. Việc duyệt vẫn do người.
- Đối chiếu danh bạ: tra `employees` theo mã NV để kiểm tra họ tên và cấp bậc. Họ tên đầu phiếu bị OCR sai nhưng tên đúng xuất hiện ở phần chữ ký thì chỉ ghi chú (`info`), không cảnh báo.

**Quy tắc đã cài (theo `SVT-QD-005`, 08/2025/QĐ-SVT):** định mức khách sạn theo thành phố và cấp bậc (Điều 5, +30% cho `truong-phong` hoặc `executive`), taxi 500.000 đ/ngày (Điều 4.4), phụ cấp lưu trú 300.000 đ/ngày và không áp dụng nội thành Hà Nội (Điều 1.2, 3), hóa đơn/vé bắt buộc với đi lại, khách sạn, taxi (Điều 4.3, 4.4), khoản ngoài danh mục như tiếp khách, hạn quyết toán 7 ngày làm việc (Điều 7.1), người phê duyệt theo tổng tiền (Điều 8.2, chỉ ghi chú). Khi không tra được cấp bậc thì áp định mức chuẩn và ghi chú.

**Chưa kiểm được (thiếu dữ liệu đầu vào):** tạm ứng tối đa 80% dự toán (Điều 6), hóa đơn điện tử đúng tên và mã số thuế công ty (Điều 7.3), thanh toán không tiền mặt cho hóa đơn từ 5 triệu (Điều 7.4), ngày nghỉ lễ khi đếm ngày làm việc.

**Giả định cần xác nhận:** "Cấp Trưởng phòng trở lên" (Điều 5.3) được hiểu là vai trò `truong-phong` hoặc `executive` trong bảng `employees`; vì vậy cấp L4 như Giám đốc dự án không được cộng 30%. Chưa xác nhận với phòng Nhân sự/Tài chính.

**Kết quả chạy thật (Tesseract + qwen3-4b qua LocalAI + Postgres, 2026-11-23):**

| Phiếu | Kết quả | Thời gian |
|---|---|---|
| NV018 | Đúng 4 lỗi theo đáp án: khách sạn vượt 750.000 đ, taxi vượt 350.000 đ, tiếp khách ngoài danh mục, quyết toán trễ 8 ngày làm việc. Không có lỗi thừa | khoảng 7 giây |
| NV017 | 0 lỗi; 1 cảnh báo (không đọc được ô hóa đơn dòng taxi) nên `needs_review = true`. Khi ô đó được OCR đọc đúng thì sạch hoàn toàn (`needs_review = false`, đã có test) | 7 đến 13 giây |

Đáp án nói NV017 hợp lệ; hệ thống chặt hơn đáp án một chút vì từ chối đoán ô hóa đơn bị mất. Đó là chủ ý.

### 3b. PaddleOCR-VL-1.6 thay Tesseract làm engine mặc định (2026-11-24)

Lý do đổi: Tesseract đọc kém trên ảnh thật; Unlimited-OCR không chạy được trên card 8 GB. Số đo trên `data/scan` (ảnh sạch giả lập, `eval.py`, cùng đường chạy của API):

| Phép đo | Tesseract | PaddleOCR-VL |
|---|---|---|
| TB-018 PNG: CER / WER | 3,9% / 6,5% | **3,2% / 4,5%** |
| TB-018 PDF scan: CER / WER | 4,1% / 7,5% | **3,3% / 5,0%** |
| Trường phiếu NV017 / NV018 | 11/12 và 13/13 | **12/12 và 13/13** |
| `/extract` NV018 | đúng 4 lỗi | đúng 4 lỗi |
| `/extract` NV017 | `needs_review = true` (không đọc được ô HĐ) | **`needs_review = false`** (đọc đủ cột HĐ) |
| Thời gian một trang | 1,5–2 giây | 16–25 giây (lần đầu thêm ~10 giây nạp model) |

Ba điều đã học được (chi tiết ở `ocr-engine/README.md`):
1. `generation_config.json` của model đặt `use_cache: false`: không truyền `use_cache=True` thì chậm gấp ~10 lần (mỗi token tính lại cả chuỗi và cả bộ mã hoá ảnh).
2. Đọc nguyên trang thì bảng ra theo CỘT. Cách sửa: dò khung bảng từ đường kẻ ngang dài, cắt thành [trên | bảng | dưới], đọc từng vùng bằng `OCR:`, nối lại (`app/ocr/layout.py`, backend lo; server chỉ đọc một ảnh).
3. Server nạp model lười và nhả VRAM sau `PADDLE_VL_IDLE_SECONDS` (30 giây) để chat (qwen3-4b, 7,4 GB) còn chỗ.

`OCR_FALLBACK_ENGINE=tesseract`: nếu engine MẶC ĐỊNH chưa sẵn sàng (server OCR tắt) thì rơi về Tesseract thay vì 503, và kết quả ghi đúng engine đã đọc. Chọn đích danh engine khác mà nó tắt thì vẫn 503.

**Giới hạn của số đo:** chỉ 1 văn bản và 2 phiếu, đều là ảnh sạch giả lập; chưa thử ảnh chụp thật (nghiêng nhiều, bóng, mờ), bảng không viền, nhiều bảng hay bảng nhiều trang. Bộ dò khung bảng dựa vào ngưỡng đặt tay và có thể hỏng với ảnh thật.

## Các phương án đã cân nhắc

| Phương án | Vì sao không chọn |
|---|---|
| Chạy Unlimited-OCR làm engine duy nhất | Chưa có bằng chứng hỗ trợ tiếng Việt; cần GPU lớn; máy demo không đủ VRAM |
| Nạp model Unlimited-OCR trực tiếp vào tiến trình FastAPI (Transformers) | `infer()` đồng bộ, không batching, mỗi worker nạp một bản model; chỉ hợp để thử nghiệm |
| Sửa thẳng `ingest.py` để có API OCR | Đang bị session khác sửa; trộn OCR dùng riêng với pipeline nạp kho |
| Tự động đưa kết quả OCR vào kho tri thức | Văn bản OCR chưa qua kiểm duyệt, chưa gắn quyền theo ADR-001, có thể chứa chỉ dẫn độc hại |
| Dùng LLM có vision (Claude) làm engine mặc định | Đắt; dữ liệu rời hạ tầng; không phù hợp tài liệu Mật. Vẫn có thể thêm thành engine tùy chọn sau |
| Lưu ảnh gốc để tra lại | Tăng rủi ro lộ dữ liệu nhạy cảm; nhu cầu chưa chứng minh |
| Để LLM phân loại khoản chi, đọc cột hóa đơn và phán vi phạm | Đã thấy qwen3-4b bịa cột hóa đơn; kết quả không giải thích và không test được. Chọn: LLM chỉ chép, mã tất định kiểm tra |
| Đổi `--psm` hoặc chỉ khử nhiễu để sửa lỗi đọc bảng | Đã đo: không sửa được số tiền trong bảng; xóa đường kẻ mới là yếu tố quyết định |

## Hệ quả

- **Tốt:**
  - Có API OCR dùng ngay với Tesseract, không phụ thuộc GPU hay model mới.
  - Thêm hoặc đổi engine không đổi router và không đổi giao diện.
  - Nghiệp vụ chỉ cài một lần ở `app/ocr`, sau này MCP và portal dùng chung.
  - Chọn engine và tiền xử lý dựa trên số đo, không dựa trên giới thiệu.
  - Trích xuất giải thích được: mỗi phát hiện có mã, điều khoản và số tiền vượt; model sai thì bị mã tất định bắt.
- **Phải trả:**
  - Thêm một package, một bảng `ocr_jobs`, phụ thuộc `numpy` (khai báo trong `pyproject.toml`). Thư mục `ocr-engine/` chỉ cần khi làm engine `unlimited`.
  - Có thêm một bản logic phát hiện lớp text trong `app/ocr/pdf.py` cho đến khi `ingest.py` chuyển sang dùng nó (trùng lặp tạm thời).
  - Quy định công tác phí được mã hóa trong `app/ocr/schemas/cong_tac_phi.py` (định mức, điều khoản). **Khi `SVT-QD-005` đổi thì phải sửa tay** hằng số ở đó; chưa đọc từ kho tri thức.
  - Đồng bộ `/extract` giữ một luồng 7 đến 13 giây; nhiều người gọi cùng lúc sẽ xếp hàng sau LLM cục bộ.
- **Thay đổi kéo theo ở phần dùng chung:**
  - `app/db.py`: thêm `connect_timeout=5`. Trước đó khi Postgres chưa sẵn sàng mọi kết nối treo vô hạn nên `/readyz` không trả được 503. Ảnh hưởng cả `knowledge-mcp`.
  - `app/main.py`: thêm `lifespan` chạy nền (tạo bảng `ocr_jobs`, đánh dấu job gián đoạn).
- **Rủi ro còn lại:**
  - CER tiếng Việt của `unlimited` có tốt hơn Tesseract không: **chưa có số liệu**.
  - Tiền xử lý và quy tắc chưa thử trên ảnh chụp thật; với ảnh thật, OCR sẽ làm mất nhiều ô hơn, dự kiến sinh nhiều cảnh báo hơn chứ không phải nhiều lỗi giả hơn, nhưng chưa đo.
  - **Starlette giữ file upload lớn (trên 1 MB) trong một tệp tạm trên đĩa** cho đến hết request, và đọc cả file trước khi kiểm tra đăng nhập. Điều này lệch với câu "không ghi file gốc xuống đĩa" ở mức hạ tầng; nên đặt giới hạn dung lượng ở BFF/proxy. Dữ liệu ứng dụng (DB, log, `ocr_jobs`) thì không chứa file gốc.
  - Dịch vụ GPU ngoài (nếu dùng) có trả lời đủ nhanh và ổn định không.
  - Nếu `LLM_PROVIDER=claude` thì văn bản phiếu rời khỏi máy; chỉ dùng cho tài liệu không thuộc diện Mật (SVT-CS-007 Điều 5).

## Ca kiểm thử bắt buộc và trạng thái

Ký hiệu: **✅** đã có test tự động (và/hoặc đã chạy thật); **⏳** chưa làm được.

| # | Ca | Trạng thái |
|---|---|---|
| 1 | `/recognize` với PDF chỉ có ảnh (`SVT-TB-018`): mọi trang nguồn `ocr`; PDF có lớp text: nguồn `text-layer`, không gọi engine | ✅ (chạy thật với Tesseract) |
| 2a | Không có token: 401 | ✅ |
| 2b | Người dùng đã nghỉ việc bị chặn ở lần gọi tiếp theo | ⏳ Chưa làm: phụ thuộc cách xác thực mới (`get_principal`), JWT cũ không kiểm tra trạng thái nhân sự |
| 3 | File sai loại (đuôi `.png` nhưng là mã thực thi), file vượt dung lượng, PDF vượt số trang: bị từ chối, không chạy OCR, không ghi vết | ✅ |
| 4 | Tắt SGLang: `/engines` báo `unavailable`; engine mặc định vẫn chạy; chọn `unlimited` nhận 503 | ⏳ Mới kiểm với engine giả (503 và `unavailable` đúng); engine `unlimited` chưa có |
| 5 | Người A tạo job; B (không phải admin) gọi job của A: 404. Admin xem được và có đúng một dòng audit; admin xem mà ghi vết lỗi thì không trả nội dung | ✅ |
| 6a | Job quá hạn bị coi như không tồn tại và bị dọn; DB không có tên file | ✅ |
| 6b | Không có file gốc nào ghi xuống đĩa | ⚠️ Chỉ đúng ở tầng ứng dụng; xem rủi ro về tệp tạm của Starlette |
| 7 | `/extract` NV017: không vi phạm; NV018: đúng 4 vi phạm, `needs_review = true` | ✅ NV018 đúng đáp án. NV017: 0 lỗi, `needs_review = false` chỉ khi OCR đọc được ô hóa đơn dòng taxi (đã test); với OCR hiện tại là `true` do 1 cảnh báo |
| 8 | `eval.py` chạy được trên `data/scan/` và xuất CER cho từng engine | ✅ Tesseract; ⏳ `unlimited` |
| 9 | Hủy job đang chạy: worker dừng sau trang hiện tại, không ghi vết `ocr_run` | ✅ |
| 10 | Khởi động lại máy chủ: job đang dở được đánh dấu `failed` | ✅ (hàm `recover_interrupted`); chưa thử khởi động lại thật |
| 11 | Model bịa số tiền, ngày hoặc cột hóa đơn: bị phát hiện, không thành lỗi giả | ✅ |

## Việc còn lại

1. Engine `unlimited` + `ocr-engine/`, rồi đo CER cùng bộ `data/scan/` để quyết định engine mặc định (mục 3).
2. Thêm mẫu thử: ảnh chụp thật (nghiêng, bóng, mờ), nhiều trang, nhiều loại phiếu.
3. `/extract` chạy nền qua `/jobs` (hiện đồng bộ), và SSE tiến độ.
4. Đổi `ingest.py` sang dùng `app/ocr/pdf.py` khi session đang sửa file đó xong.
5. Chặn người đã nghỉ việc và `GET /api/me` khi chốt phương án đăng nhập mới.
6. Xác nhận với Tài chính/Nhân sự: định nghĩa "Trưởng phòng trở lên"; tính ngày nghỉ lễ; có cần đọc định mức từ kho tri thức thay vì hằng số.
7. MCP tool gọi cùng `app/ocr` nếu cần dùng từ chat (cần giải quyết cách chuyển file).
