"""Server OCR nhỏ cho PaddleOCR-VL-1.6: một việc duy nhất, đọc MỘT ảnh -> văn bản. Chạy trong image svt-ocr-engine.

    POST /ocr  (multipart: file=ảnh, prompt="OCR:")  ->  {"text", "tokens", "ms"}
    GET  /health                                       ->  {"status": "ok", "loaded": bool, ...}

Bố cục (cắt bảng) do backend lo (backend/app/ocr/layout.py), server không biết gì về trang hay bảng.

Hai điều quan trọng đã đo trên RTX 2060 Super 8 GB (README.md):
- generate() PHẢI có use_cache=True (generation_config.json của model đặt use_cache=false -> chậm gấp ~10 lần).
- Model nạp lười (lần gọi đầu ~10 giây) và NHẢ VRAM sau PADDLE_VL_IDLE_SECONDS không có việc, để chat (qwen3-4b, 7,4 GB)
  còn chỗ. Hệ quả: gọi OCR rồi gọi chat ngay trong vài giây có thể thiếu VRAM; đặt thời gian rảnh ngắn nếu cần.
"""

import io
import os
import threading
import time

import torch
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor

MODEL_DIR = os.environ.get("PADDLE_VL_MODEL", "/models/paddleocr-vl-1.6")
MAX_PIXELS = int(os.environ.get("PADDLE_VL_MAX_PIXELS", "1003520"))  # = max_pixels trong preprocessor_config.json
IDLE_SECONDS = float(os.environ.get("PADDLE_VL_IDLE_SECONDS", "30"))
MAX_NEW_TOKENS = int(os.environ.get("PADDLE_VL_MAX_NEW_TOKENS", "2048"))
MAX_UPLOAD_MB = float(os.environ.get("PADDLE_VL_MAX_UPLOAD_MB", "30"))
# Chỉ nhận các câu lệnh của model; không cho client đưa câu lệnh tuỳ ý vào model.
PROMPTS = {"OCR:", "Table Recognition:", "Formula Recognition:", "Chart Recognition:", "Seal Recognition:"}

app = FastAPI(title="paddle-vl-ocr")
_lock = threading.Lock()  # một lượt tại một thời điểm (GPU nhỏ) và bảo vệ việc nạp/nhả model
_model = None
_processor = None
_last_used = 0.0


def _load() -> None:
    global _model, _processor
    if _model is None:
        _model = (
            AutoModelForImageTextToText.from_pretrained(MODEL_DIR, dtype=torch.float16, attn_implementation="sdpa")
            .to("cuda")
            .eval()
        )
        _processor = AutoProcessor.from_pretrained(MODEL_DIR)


def _unload() -> None:
    global _model, _processor
    _model = _processor = None
    torch.cuda.empty_cache()


def _janitor() -> None:
    while True:
        time.sleep(5)
        with _lock:
            if _model is not None and time.time() - _last_used > IDLE_SECONDS:
                _unload()


threading.Thread(target=_janitor, daemon=True).start()


def _fit(img: Image.Image) -> Image.Image:
    """Thu nhỏ để số điểm ảnh <= MAX_PIXELS: bản transformers này bỏ qua `size` của processor, ảnh lớn làm bộ mã hoá ảnh
    tốn hàng GB VRAM và chạy rất chậm."""
    scale = (MAX_PIXELS / (img.width * img.height)) ** 0.5
    if scale >= 1:
        return img
    size = (max(28, int(img.width * scale) // 28 * 28), max(28, int(img.height * scale) // 28 * 28))
    return img.resize(size, Image.LANCZOS)


@app.get("/health")
def health():
    return {"status": "ok", "loaded": _model is not None, "model": os.path.basename(MODEL_DIR)}


@app.post("/ocr")
def ocr(file: UploadFile = File(...), prompt: str = Form("OCR:")):
    global _last_used
    if prompt not in PROMPTS:
        raise HTTPException(400, f"Câu lệnh không được phép: {prompt!r}")
    data = file.file.read(int(MAX_UPLOAD_MB * 1024 * 1024) + 1)
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"Ảnh vượt giới hạn {MAX_UPLOAD_MB:g} MB")
    try:
        image = _fit(Image.open(io.BytesIO(data)).convert("RGB"))
    except Exception as e:  # noqa: BLE001 - không phải ảnh
        raise HTTPException(400, "Không đọc được ảnh") from e

    t0 = time.time()
    with _lock:
        _load()
        messages = [{"role": "user", "content": [{"type": "image", "image": image}, {"type": "text", "text": prompt}]}]
        inputs = _processor.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt"
        ).to(_model.device)
        with torch.no_grad():
            out = _model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS, do_sample=False, use_cache=True)
        start = inputs["input_ids"].shape[-1]
        text = _processor.decode(out[0][start:-1])
        _last_used = time.time()
    return {"text": text, "tokens": int(out.shape[-1] - start), "ms": int((time.time() - t0) * 1000)}
