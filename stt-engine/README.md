# stt-engine: server chuyển giọng nói thành văn bản (ADR-006, giai đoạn 2)

Một việc duy nhất: nhận MỘT file WAV 16 kHz mono, trả các đoạn lời nói theo từng dòng NDJSON.
Backend (`backend/app/stt/engines/whisper.py`) là client; ffmpeg, tiến độ, hủy job, quyền đều ở backend.

```
POST /transcribe?language=vi   (multipart: file=WAV)  ->  {"start","end","text"} từng dòng ... {"done": true, "duration", "ms"}
GET  /health                                          ->  {"status":"ok","loaded":bool,"model","device","compute_type"}
```

## Chạy

```powershell
cd stt-engine
./convert-phowhisper.ps1                    # một lần: chuyển PhoWhisper-small sang CTranslate2 int8 (~240 MB) vào models/
./run.ps1                                   # tạo .venv, chạy server ở 127.0.0.1:10002; mặc định dùng models/phowhisper-small
```
Rồi đặt `STT_WHISPER_URL=http://127.0.0.1:10002` trong `backend/.env` và khởi động lại backend. Server tắt: `/api/stt/engines`
báo `available: false`, tạo job nhận 503.

Cấu hình bằng biến môi trường (xem đầu `server/whisper_server.py`): `STT_MODEL` (mặc định PhoWhisper-small nếu đã chuyển đổi, không thì large-v3-turbo; còn có large-v3, medium, small, large-v3, medium, small, hoặc
đường dẫn model đã chuyển đổi như PhoWhisper), `STT_DEVICE` (cpu|cuda), `STT_COMPUTE_TYPE` (cpu: int8; cuda: float16),
`STT_IDLE_SECONDS` (nhả model sau bao lâu rảnh, mặc định 60).

## Cắt đoạn và phân biệt người nói
- Server cắt âm thanh theo **khoảng lặng** (Silero VAD, đoạn tối đa 20 giây) rồi chép từng đoạn, thay vì để Whisper tự chia khối 30 giây:
  PhoWhisper không có mốc thời gian theo câu nên cả khối thành một đoạn và câu ở ranh giới bị rơi mất.
- Nếu có `models/diarization/segmentation.onnx` và `embedding.onnx` (pyannote-segmentation-3-0 + 3D-Speaker ERes2Net, từ
  GitHub k2-fsa/sherpa-onnx, ~45 MB), mỗi đoạn được gán nhãn `A`, `B`, ... theo thứ tự xuất hiện. Không biết trước số người hay tên.
  Thiếu model: vẫn chép lời, không nhãn (`/health` báo `diarization: false`).
- Chỉnh bằng `STT_DIAR_THRESHOLD` (mặc định 0,7; cao hơn = gộp thành ít người hơn) và query `speakers=N` nếu biết số người.

## Đã kiểm
- File thử 97 giây (2 giọng TTS luân phiên): 21 đoạn theo câu, WER 10%, nhãn người nói khớp đáp án 100%. Ngưỡng 0,5 tách nhầm thành 6
  người, 0,7 đến 0,9 ra đúng 2. Giọng TTS rất khác nhau nên đây là ca DỄ; giọng thật, nói chồng, hai người giống giọng chưa thử.
- Phân tách người nói tốn thêm khoảng 0,25 lần thời lượng (4 luồng CPU); cả job ~1,1 lần thời lượng gồm lúc nạp model.
- Server + client + ffmpeg chạy thông suốt trên máy này (CPU int8, model `small`, giọng đọc tiếng Anh tổng hợp 8,7 giây: đúng
  nguyên văn, RTF ~0,4 gồm cả lúc nạp model).
- Chạy trên host (không Docker) vì không cần GPU để bắt đầu; chuyển vào container sau nếu muốn đồng bộ với `ocr-engine/`.

## CHƯA kiểm
- **PhoWhisper-small** đã chuyển đổi và nạp được (chạy CPU int8, ~4,5 giây cho 8,7 giây âm thanh gồm nạp model), nhưng tôi không có ghi âm tiếng Việt để thử. Khi ép `language=vi` lên giọng tiếng Anh nó bịa ra một câu tiếng Việt: PhoWhisper chỉ nên dùng cho tiếng Việt, cuộc họp lẫn nhiều tiếng Anh có thể bị sai.
- **Chất lượng tiếng Việt**: chưa có ghi âm họp thật. Số trên chỉ chứng minh đường ống chạy, không nói gì về WER tiếng Việt.
- **GPU (`STT_DEVICE=cuda`)**: chưa thử (cần cuBLAS + cuDNN 9; lúc viết GPU đã bị chiếm ~6 GB bởi tiến trình khác).
- Whisper hay "bịa" chữ ở đoạn im lặng/ồn: đã bật `vad_filter` và tắt `condition_on_previous_text`, chưa đo hiệu quả.

## Đo để chọn engine mặc định
Đặt vài cặp `ten.mp3` + `ten.txt` (bản gỡ băng đúng) vào một thư mục, rồi (đứng ở `backend/`, server đang chạy):
```powershell
$env:STT_WHISPER_URL="http://127.0.0.1:10002"; .venv\Scripts\python.exe -m app.stt.eval <thư-mục> --engine whisper --language vi
```
So sánh các `STT_MODEL`/`STT_DEVICE` bằng cùng bộ file; đừng chọn theo giới thiệu của model.

## Lưu ý phiên bản
`requirements.txt` ghim `av<17`: `av` 19 bỏ tham số mà faster-whisper 1.2.1 còn truyền, giải mã lỗi `TypeError: ... metadata_errors`.
