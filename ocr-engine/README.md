# ocr-engine: server Unlimited-OCR-2 (SGLang)

Chạy `baidu/Unlimited-OCR-2` (MIT, 3B, trọng số 6,9 GB) bằng bản SGLang tuỳ biến của chính repo model. Backend chỉ là
client HTTP (`backend/app/ocr/engines/unlimited.py`, biến `OCR_SGLANG_*`). Xem ADR-005 mục 2, 6.

| File | Việc |
|---|---|
| `download-model.sh` | Tải model và wheel về `model/` (bị `.gitignore`). Chạy lại được. |
| `Dockerfile` | Ubuntu 22.04 + Python 3.10 + wheel SGLang (image ~8,4 GB). `docker build -t svt-ocr-engine:dev .` |
| `run.sh` | Chạy container `svt-ocr` ở `127.0.0.1:10000`. Tắt `local-ai` trước (GPU 8 GB). |
| `run-paddle.sh` | Chạy server PaddleOCR-VL (`svt-ocr-paddle`, `127.0.0.1:10001`), tự khởi động lại cùng Docker. **Đây là server đang dùng.** |
| `server/paddle_vl_server.py` | Server nhỏ: `POST /ocr` (một ảnh -> văn bản), `GET /health`. Nạp lười, nhả VRAM khi rảnh. |
| `download-paddleocr-vl.sh` | Tải PaddleOCR-VL-1.6 (1,9 GB) về `models/`. |
| `logit-processor.txt` | Chuỗi `custom_logit_processor` (chống lặp n-gram) cho `OCR_SGLANG_LOGIT_PROCESSOR`. |

## Kết quả thử trên RTX 2060 Super 8 GB (2026-11-24): KHÔNG chạy được

Đã vượt các lỗi dựng: backend attention bắt buộc là `unlimited_ocr_v2` (không dùng `triton`), cần `CUDA_HOME` trỏ tới
nvcc đi kèm gói torch cu13 (`nvidia/cu13`), phải bỏ `expandable_segments` thì mới nạp được trọng số.

Nhưng sau khi nạp (`--dtype float16`, Turing không có BF16) trọng số chiếm **6,96 GB = toàn bộ VRAM trống**
(`avail mem=0.00 GB`), không còn chỗ cho KV cache và activation; SGLang từ chối khởi động (cần mem-fraction ≥ 0,94).
`--cpu-offload-gb` không có tác dụng với lớp MoE của model này (và máy chỉ còn ~1,4 GB RAM trống).
Các lớp expert là tham số gói (không phải `nn.Linear`) nên cũng không lượng tử hoá được bằng torchao/bitsandbytes
trong SGLang.

Kết luận: cần GPU từ khoảng 16 GB (card 24 GB là mức model card khuyến nghị) hoặc đổi cách chạy (xem ADR-005).

## PaddleOCR-VL-1.6 (thử 2026-11-24): chạy được trên card 8 GB

Tải bằng `download-paddleocr-vl.sh` (1,9 GB, Apache-2.0). Thử bằng `probe_paddle_vl.py` trong image `svt-ocr-engine:dev`
(đã có transformers 5.x), mount `models/` và `data/scan/`:

```
docker run --rm --gpus all -v <repo>/ocr-engine/models:/models:ro -v <repo>/data/scan:/scan:ro \
  -v <repo>/data/eval/reports/ocr-raw/paddleocr-vl-probe:/out -v <repo>/ocr-engine/probe_paddle_vl.py:/probe.py:ro \
  svt-ocr-engine:dev python /probe.py fp16 "OCR:" 1003520
```

- Model nạp ~9 giây, chiếm 1,7 GiB VRAM (đỉnh 2,0 GiB): không cần tắt `local-ai` nếu chat chưa nạp model.
- **Bẫy tốc độ:** `generation_config.json` của model đặt `"use_cache": false`. Không truyền `use_cache=True` vào `generate()` thì mỗi
  token tính lại toàn bộ chuỗi và chạy lại cả bộ mã hoá ảnh: 2,5 token/giây, một trang mất 4–6 phút. Có `use_cache=True`: ~23
  token/giây, **16–21 giây một trang**, kết quả giống hệt.
- Ảnh phải tự thu nhỏ về ≤ 1.003.520 điểm (bản transformers này bỏ qua `size` của processor).
- Kết quả trên `data/scan` (ảnh sạch giả lập), PaddleOCR-VL so với Tesseract: văn bản TB-018 CER 3,2% so với 4,1%, WER 4,5% so với
  7,5%; trường phiếu NV017 12/12 so với 11/12, NV018 13/13 so với 13/13.
- **Bảng ra theo cột khi chạy nguyên trang** (cả cột tên khoản, rồi cột số lượng, rồi cột tiền): `/extract` cần mỗi dòng bảng
  nằm trên một dòng. **Cách sửa đã thử (`probe_split.py`):** dò khung bảng từ các đường kẻ ngang dài (> 60% bề rộng, làm dày
  dọc 10 điểm để chịu ảnh nghiêng nhẹ), cắt trang thành [phần trên | bảng | phần dưới], OCR từng phần bằng câu lệnh `OCR:` rồi
  nối lại. Kết quả: mỗi dòng bảng nằm trên một dòng (`1 Vé máy bay khứ hồi HN - HCM 1 4.280.000 Có`), đủ cột HĐ (`Có`, `-`,
  `Không`), cả NV017 và NV018; mất 20–25 giây một trang. `Table Recognition:` trả bảng dạng OTSL (`<fcel>...<nl>`) cũng đúng
  trên phần đã cắt, nhưng chạy trên nguyên trang thì NV017 mất cột (không dùng).
- Chưa kiểm: ảnh nghiêng nhiều, bảng không có đường kẻ, nhiều bảng trên một trang, bảng nhiều trang.

## Engine `paddleocr_vl` trong backend (đang dùng)

`./run-paddle.sh` rồi trong `backend/.env`: `OCR_ENGINE=paddleocr_vl`, `OCR_PADDLEVL_URL=http://127.0.0.1:10001`,
`OCR_FALLBACK_ENGINE=tesseract`. Backend cắt trang ở khung bảng (`app/ocr/layout.py`) và gọi `POST /ocr` cho từng vùng.
Server tắt thì API tự rơi về Tesseract. `PADDLE_VL_IDLE_SECONDS` (mặc định 30) là thời gian rảnh trước khi nhả VRAM; gọi
chat ngay sau OCR trong vài giây có thể thiếu VRAM (qwen3-4b cần 7,4 GB), đặt giá trị nhỏ hơn nếu gặp.

## Dọn dẹp (2026-11-24)

Trọng số Unlimited-OCR-2 (6,7 GB) đã xoá khỏi `model/` vì không chạy được trên card 8 GB. Giữ lại `model/wheel/` (15 MB) vì
`Dockerfile` cần wheel SGLang để build image `svt-ocr-engine:dev` (image này cũng là nền cho server PaddleOCR-VL). Cần tải lại
wheel: `WHEEL_ONLY=1 ./download-model.sh`.
