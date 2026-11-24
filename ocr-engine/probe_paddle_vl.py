"""Thử nhanh PaddleOCR-VL-1.6 bằng transformers trên các ảnh data/scan (chạy trong container svt-ocr-engine).

Chỉ để đo thử: gửi nguyên trang với câu lệnh "OCR:". Cách chính thức của model là layout -> từng khối rồi mới OCR từng khối
(paddleocr[doc-parser]); chạy nguyên trang là cách đơn giản, có thể kém hơn.
"""
import sys
import time
from pathlib import Path

import torch
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor

MODEL = "/models/paddleocr-vl-1.6"
DTYPE = {"fp16": torch.float16, "bf16": torch.bfloat16, "fp32": torch.float32}[sys.argv[1] if len(sys.argv) > 1 else "fp16"]
PROMPT = sys.argv[2] if len(sys.argv) > 2 else "OCR:"
MAX_PIXELS = int(sys.argv[3]) if len(sys.argv) > 3 else 1003520  # max_pixels trong preprocessor_config.json
OUT = Path("/out") / f"{sys.argv[1] if len(sys.argv) > 1 else 'fp16'}"
OUT.mkdir(parents=True, exist_ok=True)

t0 = time.time()
model = AutoModelForImageTextToText.from_pretrained(MODEL, torch_dtype=DTYPE).to("cuda").eval()
processor = AutoProcessor.from_pretrained(MODEL)
print(f"nạp model {time.time() - t0:.1f}s, VRAM {torch.cuda.memory_allocated() / 2**30:.2f} GiB", flush=True)

for png in sorted(Path("/scan").glob("*.png")):
    image = Image.open(png).convert("RGB")
    # Bản transformers này bỏ qua images_kwargs size: tự thu nhỏ để số điểm ảnh <= MAX_PIXELS (nếu không, ảnh gốc ~8 triệu
    # điểm làm bộ mã hoá ảnh tốn hàng GB VRAM và chạy rất chậm).
    scale = (MAX_PIXELS / (image.width * image.height)) ** 0.5
    if scale < 1:
        image = image.resize((max(28, int(image.width * scale) // 28 * 28), max(28, int(image.height * scale) // 28 * 28)), Image.LANCZOS)
    print(f"{png.name}: ảnh đưa vào model {image.size}", flush=True)
    messages = [{"role": "user", "content": [{"type": "image", "image": image}, {"type": "text", "text": PROMPT}]}]
    inputs = processor.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt",
    ).to(model.device)
    t = time.time()
    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=2048, do_sample=False, use_cache=True)
    text = processor.decode(outputs[0][inputs["input_ids"].shape[-1]:-1])
    (OUT / f"{png.stem}.txt").write_text(text, encoding="utf-8")
    print(f"== {png.name}: {time.time() - t:.1f}s, {outputs.shape[-1] - inputs['input_ids'].shape[-1]} token, "
          f"đỉnh VRAM {torch.cuda.max_memory_allocated() / 2**30:.2f} GiB", flush=True)
    print(text[:700], flush=True)
