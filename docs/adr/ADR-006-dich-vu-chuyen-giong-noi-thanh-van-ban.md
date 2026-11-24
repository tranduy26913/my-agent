# ADR-006: Dịch vụ chuyển ghi âm cuộc họp thành văn bản (STT), engine thay được

- Trạng thái: **Đang triển khai, giai đoạn 1 (backend) xong** (2026-11-24): API, job, chuyển đổi ffmpeg và test đã có, dùng engine giả. Chưa có engine thật, chưa đo chất lượng tiếng Việt, chưa có giao diện portal.
- Liên quan: ADR-005 (dịch vụ OCR: mẫu được bám theo), ADR-004 (Portal + Chat, một nghiệp vụ hai cách gọi), ADR-001 (phân quyền tài liệu), `docs/07-khung-giao-dien-portal.md`
- Phạm vi: **chỉ chuyển giọng nói thành văn bản có mốc thời gian.** Tóm tắt thành biên bản, nhận diện người nói và nạp vào kho tri thức nằm ngoài ADR này (xem "Việc còn lại").

## Bối cảnh

1. Portal đã có công cụ OCR (`/tools/ocr`, ADR-005). Người dùng muốn thêm một công cụ cùng kiểu: tải file ghi âm cuộc họp lên, nhận lại văn bản.
2. Khác OCR ở những điểm làm đổi thiết kế:
   - Cuộc họp dài 30 đến 120 phút. Xử lý mất từ vài phút đến hàng chục phút, nên **không thể có chế độ đồng bộ**.
   - File lớn: MP3 2 giờ cỡ 100 MB, WAV hoặc video họp (MP4 từ Teams/Zoom) có thể hàng trăm MB. ADR-005 giữ file trong RAM; ở đây không được.
   - Ghi âm cuộc họp **nhạy cảm hơn ảnh phiếu**: có thể chứa lương, nhân sự, chiến lược.
3. Máy demo: RTX 2060 Super 8 GB, đang dùng khoảng 7,3 GB cho `qwen3-4b`; CPU Ryzen 5 5500 (6 nhân, 12 luồng); RAM khả dụng rất sát (`docs/05` mục 4.1). Không có chỗ rộng rãi cho một model nhận dạng giọng nói thường trú.
4. `pyproject.toml` đã có nhóm tùy chọn `audio = ["faster-whisper"]`, nhưng chưa có mã nào dùng.
5. Chưa biết engine nào đọc tốt tiếng Việt trong phòng họp (nhiều người nói, tiếng ồn, từ chuyên ngành, lẫn tiếng Anh). Ứng viên: Whisper large-v3 hoặc large-v3-turbo qua faster-whisper; PhoWhisper (tinh chỉnh cho tiếng Việt). **Chưa có số đo nào.**

## Quyết định

### 1. STT là một service riêng ở tầng nghiệp vụ, bám mẫu của OCR
- Package mới `app/stt/` (`service.py`, `jobs.py`, `audio.py`, `engines/`), router mỏng `app/api/stt.py` ở `/api/stt`. Router chỉ nhận request, kiểm quyền, gọi service, ghi vết.
- Không sửa code OCR. `jobs.py` của STT **trùng khoảng 150 dòng** với `app/ocr/jobs.py` (tạo, đọc theo chủ, xóa, dọn hết hạn, khôi phục). Chấp nhận trùng lặp tạm thời để không đụng OCR đang chạy; khi có loại job thứ ba thì tách phần chung.
- Nếu sau này cần gọi từ chat: thêm MCP server mỏng gọi cùng service (như ADR-004), không viết lại nghiệp vụ.

### 2. Engine thay được qua một giao diện sinh từng đoạn
```
transcribe(audio_path: str, *, language: str | None) -> Iterator[Segment]   # Segment = (start, end, text), đơn vị giây
```
- `audio_path` là WAV 16 kHz mono do service chuẩn bị; engine không phải biết về định dạng gốc.
- Trả **iterator** (không phải danh sách) để service tính tiến độ theo giây âm thanh đã xong và dừng được giữa chừng khi job bị hủy.
- Đăng ký trong dict `ENGINES` như OCR. Chọn bằng `STT_ENGINE` và tham số `engine`. Tên sai: 400. Engine chưa sẵn sàng: 503.
- **Giai đoạn 1 chưa đăng ký engine thật nào.** `ENGINES` rỗng; test dùng `FakeEngine` đăng ký vào đúng dict này (như OCR). Hợp đồng HTTP với server engine (stream NDJSON hay chia cửa sổ) sẽ chốt ở giai đoạn 2 cùng lúc với server, không đoán trước.

### 3. Luôn bất đồng bộ
- Chỉ có `/jobs` (không có `/transcribe` đồng bộ). Tạo job trả `202` kèm `job_id`; poll để biết tiến độ.
- Tiến độ là `done_s / duration_s` (giây âm thanh). Job lưu trong bảng `stt_jobs`, hàng đợi là `ThreadPoolExecutor` trong tiến trình như OCR, nhưng **mặc định 1 worker** (một lượt giải mã tại một thời điểm, vì tranh GPU/CPU).

### 4. File âm thanh: ghi tạm xuống đĩa, xóa ngay khi xong
Đây là **ngoại lệ có chủ ý** so với ADR-005 ("file gốc chỉ nằm trong RAM"):
- Router đọc upload theo khối vào một tệp tạm trong `STT_TMP_DIR` (mặc định thư mục tạm của hệ điều hành, thư mục con `svt-stt`), có chặn dung lượng. Không nạp cả file vào RAM.
- Ngay khi nhận job, `audio.probe` cho ffmpeg giải mã thử 1 giây đầu: rác, file rỗng hoặc video không có tiếng bị từ chối **ngay** bằng 400 (không tạo job, không ghi vết); thời lượng khai báo quá giới hạn bị từ chối bằng 422.
- Worker dùng **ffmpeg** đổi sang WAV 16 kHz mono (bỏ hình nếu là video), kiểm lại thời lượng thật, rồi giải mã. Loại file xác định bằng **nội dung** (ffmpeg đọc được hay không), không tin đuôi hay `Content-Type`.
- Tệp gốc và tệp WAV bị xóa trong `finally` của worker, kể cả khi thất bại hoặc bị hủy. Khi khởi động, thư mục tạm được **dọn sạch** (job dở đã bị đánh dấu `failed` nên không cần tệp nữa).
- Vì vậy mệnh đề "không có file gốc nào ghi xuống đĩa" **không đúng** cho STT, và với ADR-005 nó vốn đã chỉ đúng ở tầng ứng dụng (Starlette tự spool upload lớn ra đĩa). Điều giữ được: **không lưu lâu dài** (không trong DB, không trong `upload_dir`) và xóa ngay khi xong.
- Yêu cầu hạ tầng: thư mục tạm nằm ở ổ có chỗ trống (WAV 16 kHz mono 16 bit = 32 KB mỗi giây, 3 giờ ≈ 345 MB, cộng tệp gốc).

### 5. Giao diện REST (tiền tố `/api/stt`)

| Method | Đường dẫn | Việc làm |
|---|---|---|
| GET | `/engines` | Liệt kê engine, tình trạng, engine mặc định |
| POST | `/jobs` | Upload (multipart), tham số `engine`, `language` (mặc định `vi`). Trả `202` + `Location` |
| GET | `/jobs` | Lịch sử job của chính người gọi (không kèm văn bản) |
| GET | `/jobs/{id}` | Trạng thái, tiến độ, và khi xong: danh sách `segments` |
| DELETE | `/jobs/{id}` | Xóa job và kết quả; job đang chạy thì worker dừng ở đoạn kế tiếp |

Xuất `.txt`/`.srt` làm ở portal (giai đoạn 3), không thêm endpoint.

### 6. Dữ liệu, quyền và ghi vết (giữ nguyên quy tắc ADR-005, siết thêm)
- Mọi endpoint cần token Zitadel của nhân viên đang hoạt động (cùng cổng với OCR: `get_ocr_user`, đặt thêm tên `get_stt_user` cho dễ đọc).
- Job chỉ người tạo xem được; người khác nhận **404**. Admin xem được nhưng phải ghi audit `stt_job_view` **trước** khi trả nội dung (ghi lỗi thì không trả). Admin không xóa hộ được.
- Kết quả hết hạn sau `STT_JOB_TTL_DAYS` (mặc định 7 ngày), dọn lười biếng mỗi lần tạo job.
- Không lưu tên file. Ghi vết **không chứa tên file hay nội dung văn bản**:

| Sự kiện `AuditLog` | Khi nào |
|---|---|
| `stt_run` | Job xong (engine, số byte, thời lượng, số đoạn, thời gian xử lý, `job_id`) |
| `stt_job_failed` | Job thất bại |
| `stt_job_view` | Admin xem job của người khác |

  `UsageLog` ghi `purpose = "stt"`, model `local:<engine>`, chi phí 0.
- **Văn bản là dữ liệu không đáng tin** nếu sau này đưa vào kho tri thức hoặc cho LLM đọc (người nói có thể đọc to một câu chỉ dẫn): phải qua bước làm sạch prompt injection của P2 và gắn quyền theo ADR-001. Không tự động nạp vào kho.
- **Không có nhãn "Mật" tự động.** Cuộc họp có thể bàn nội dung Mật; chưa có cách biết. Hiện chỉ dựa vào việc kết quả riêng tư theo người dùng. Nếu sau này dùng engine ở ngoài máy thì cấm cho mọi cuộc họp (xem mục 8).

### 7. Giới hạn đầu vào (cấu hình được trong `app/config.py`)

| | Mặc định |
|---|---|
| Dung lượng file | `STT_MAX_MB` = 300 |
| Thời lượng | `STT_MAX_MINUTES` = 180 (ffmpeg dừng đọc quá mốc này; vượt thì từ chối) |
| Job đang chờ/chạy mỗi người | `STT_JOB_MAX_ACTIVE_PER_USER` = 2 |
| Job đang chờ/chạy toàn hệ thống | `STT_JOB_QUEUE_MAX` = 10 (vượt: 429) |
| Số job chạy cùng lúc | `STT_JOB_WORKERS` = 1 |
| Lượt giải mã cùng lúc mỗi engine | `STT_MAX_CONCURRENCY` = 1 |
| Ngôn ngữ mặc định | `STT_LANGUAGE` = `vi` |

- Cuộc họp dài hơn giới hạn: người dùng tự cắt file (giai đoạn đầu không tự chia).
- Job mất khi máy chủ khởi động lại; lúc khởi động được đánh dấu `failed` và người dùng gửi lại (như OCR).
- Bảng `stt_jobs` do ứng dụng tự tạo lúc khởi động (`checkfirst`, chạy luồng nền).
- Hạn chế đã biết: hạn mức hàng đợi chỉ kiểm sau khi upload xong, nên bị từ chối ở bước tạo job thì người dùng đã tải xong cả file. Chấp nhận ở giai đoạn 1.

### 8. Hạ tầng engine (làm ở giai đoạn 2, nay chỉ ghi nguyên tắc)
- Engine thật chạy trong container riêng (thư mục `stt-engine/` ở gốc dự án, tách khỏi `backend/`), nạp model lười và nhả VRAM khi rảnh, theo mẫu `ocr-engine/` (`svt-ocr-paddle`).
- Hai hướng tài nguyên, chọn **bằng số đo**:
  - GPU: nhanh nhưng tranh VRAM với `qwen3-4b`; phải nhả model khi rảnh và chấp nhận chờ nạp.
  - CPU int8: không tranh VRAM, nhưng với cuộc họp dài có thể chậm hơn thời gian thực (ước lượng, chưa đo).
- Engine ở ngoài máy (API STT của bên thứ ba): **không dùng cho cuộc họp** vì giọng nói là dữ liệu nhạy cảm; chỉ cân nhắc cho ghi âm công khai và phải có quyết định riêng.
- Backend phải chạy được khi engine tắt: `/engines` báo `available: false`, tạo job nhận 503, phần còn lại của API không ảnh hưởng.
- Image Docker cần ffmpeg riêng. Trên máy host hiện có `C:\ffmpeg\bin`; backend tìm theo thứ tự `FFMPEG_CMD`, `PATH`, `C:\ffmpeg\bin\ffmpeg.exe`.

### 9. Chọn engine mặc định theo số đo
- Cần bộ thử: vài đoạn ghi âm họp **thật** (nhiều người, có tiếng ồn) kèm bản gỡ băng làm đáp án, đo **WER** và hệ số thời gian thực (thời gian xử lý / thời lượng), chạy bằng một script đo như `app/ocr/eval.py`. Chưa có bộ này; `docs/03-mo-phong-cong-viec/tu-lieu/transcript-hop-du-an.md` là văn bản, không phải âm thanh.
- Không chọn engine mặc định theo giới thiệu của model.

## Các phương án đã cân nhắc

| Phương án | Vì sao không chọn |
|---|---|
| Có thêm endpoint đồng bộ cho file ngắn | Hai đường code cho một nhu cầu chưa có; file ngắn vẫn dùng job được. Có thể thêm sau |
| Giữ file âm thanh trong RAM như OCR | File vài chục đến vài trăm MB, nhiều người nộp cùng lúc sẽ hết RAM, vốn đã sát (ADR-005, `docs/05`) |
| Nạp Whisper thẳng vào tiến trình FastAPI | Mỗi worker uvicorn nạp một bản; chiếm RAM/VRAM thường trực; lỗi native có thể làm sập cả API |
| Dùng API STT đám mây | Giọng nói họp là dữ liệu nhạy cảm, rời hạ tầng; chi phí theo phút |
| Trả cả văn bản một lần, không có iterator | Không có tiến độ, không hủy giữa chừng được, job vài chục phút trông như treo |
| Dùng lại bảng/module job của OCR ngay | Phải sửa code OCR đang chạy thật; làm sau khi có loại job thứ ba |
| Làm luôn tóm tắt biên bản và nhận diện người nói | Mỗi cái là một bài toán riêng (ngữ cảnh qwen3-4b ngắn so với cuộc họp dài; diarization nặng); làm khi bước chuyển văn bản ổn định và có số đo |

## Hệ quả

- **Tốt:** cùng mẫu OCR nên portal, BFF, phân quyền, ghi vết dùng lại cách đã quen; đổi engine không đổi router; tiến độ và hủy job chạy được với job dài; file nhạy cảm không tồn tại lâu.
- **Phải trả:**
  - Thêm một package, một bảng `stt_jobs`, phụ thuộc ngoài là ffmpeg.
  - Trùng lặp có chủ ý với `app/ocr/jobs.py`.
  - Ghi âm nằm trên đĩa trong lúc chờ và xử lý (mục 4); thư mục tạm cần dung lượng và quyền truy cập hợp lý.
  - Cuộc họp bị cắt lúc máy chủ khởi động lại phải gửi lại từ đầu.
- **Phải đổi ở phần dùng chung:** `app/main.py` (đăng ký router, chạy `stt.jobs.startup`), `app/config.py` (nhóm `stt_*`), `app/models.py` (`SttJob`), `app/api/deps.py` (`get_stt_user`). Giai đoạn 3 thêm một dòng ở `nav.ts` và ở `ROUTES` của BFF.
- **Rủi ro còn lại:**
  - **Chất lượng tiếng Việt chưa biết.** Phòng họp thật có thể cho WER cao; kết quả cần người đọc lại.
  - **Tốc độ chưa biết** trên máy này, cả hai hướng GPU và CPU.
  - Proxy của Next.js (`src/proxy.ts` khớp cả `/api/*`) mặc định đệm tối đa 10 MB thân request; upload ghi âm sẽ bị cắt nếu không nâng `proxyClientMaxBodySize` hoặc loại `api/stt` khỏi matcher. Việc của giai đoạn 3, **chưa kiểm hành vi thật**.
  - Starlette đọc cả file upload (spool ra đĩa) trước khi kiểm quyền; giới hạn dung lượng thật nên đặt ở BFF/proxy.
  - Văn bản có thể chứa chỉ dẫn độc hại nếu sau này đưa cho LLM (mục 6).

## Ca kiểm thử bắt buộc và trạng thái

Ký hiệu: **✅** đã có test tự động; **⏳** chưa làm.

| # | Ca | Trạng thái |
|---|---|---|
| 1 | Tạo job: `202`, `Location`, chạy xong, trả `segments` có mốc thời gian, tiến độ đủ | ✅ |
| 2 | Ghi vết và riêng tư: audit/DB không chứa tên file hay nội dung; `usage` ghi đúng | ✅ |
| 3 | File không phải âm thanh (đuôi `.mp3` nhưng là mã thực thi hoặc rỗng): 400, không vào hàng đợi, không ghi vết, không để lại tệp tạm | ✅ |
| 4 | Vượt dung lượng: 413. Thời lượng khai báo vượt giới hạn: 422 ngay lúc nhận. Metadata sai mà thời lượng thật vượt: job `failed` (kiểm lại sau khi đổi sang WAV) | ✅ |
| 5 | Người A tạo job; B (không phải admin): 404. Admin xem: đúng một dòng `stt_job_view`; ghi vết lỗi thì không trả nội dung | ✅ |
| 6 | Hạn mức: quá số job mỗi người hoặc toàn hệ thống: 429 | ✅ |
| 7 | Hủy job đang chạy: worker dừng, không ghi `stt_run`, tệp tạm được xóa | ✅ |
| 8 | Engine ném lỗi hoặc chưa sẵn sàng: job `failed` với câu chung (không lộ chi tiết), tệp tạm được xóa; chọn engine tắt: 503 | ✅ |
| 9 | Job quá hạn bị coi như không tồn tại và bị dọn | ✅ |
| 10 | Khởi động: job dở bị đánh dấu `failed`; thư mục tạm được dọn | ✅ |
| 11 | Chuyển đổi và kiểm tra bằng ffmpeg thật (WAV sinh trong test; rác, file rỗng, quá dài; bỏ qua nếu máy không có ffmpeg) | ✅ (chạy thật trên máy này, ffmpeg có sẵn) |
| 12 | Đo WER và hệ số thời gian thực của engine thật trên ghi âm họp thật | ⏳ Giai đoạn 2, cần có ghi âm |

## Việc còn lại

1. Giai đoạn 2: `stt-engine/` (container, server, hợp đồng HTTP), engine client, đo WER và tốc độ, chọn mặc định.
2. Giai đoạn 3: trang `/tools/ghi-am` ở portal, dòng BFF, xử lý giới hạn 10 MB của proxy.
3. Tóm tắt thành biên bản bằng LLM cục bộ (chia nhỏ rồi gộp vì ngữ cảnh ngắn).
4. Nạp biên bản vào kho tri thức, qua bước làm sạch và phân quyền (ADR-001).
5. Nhận diện người nói.
6. Tách phần dùng chung của `jobs.py` OCR và STT.
7. Kiểm hạn mức trước khi upload (hiện kiểm sau).
