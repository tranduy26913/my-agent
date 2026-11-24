"""Thử đọc bảng của phiếu bằng PaddleOCR-VL: tự tìm khung bảng (đường kẻ), cắt rồi thử các câu lệnh."""
import os, sys, time
import numpy as np
import torch
from pathlib import Path
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor

M = "/models/paddleocr-vl-1.6"
OUT = Path("/out/split"); OUT.mkdir(parents=True, exist_ok=True)
MAX_PIXELS = 1003520


def _win_any(a, k, axis):
    c = np.cumsum(np.pad(a.astype(np.int32), [(k, k) if i == axis else (0, 0) for i in range(2)]), axis=axis)
    return (np.take(c, range(2 * k, c.shape[axis]), axis=axis) - np.take(c, range(0, c.shape[axis] - 2 * k), axis=axis)) > 0


def find_table(img, margin=30, thr=120, frac=0.6, k=10):
    """Khung bảng = vùng giữa đường kẻ ngang đầu và cuối (dài > 60% bề rộng). Làm dày dọc k điểm để chịu ảnh nghiêng nhẹ."""
    dark = np.asarray(img.convert("L")) < thr
    h, w = dark.shape
    hv = _win_any(dark, k, 0)
    ys = np.where(hv.sum(1) / w > frac)[0]
    if ys.size < 2:
        return None
    band = np.where(hv[ys].any(0))[0]
    return (int(max(0, band.min() - margin)), int(max(0, ys.min() - margin)), int(min(w, band.max() + margin)), int(min(h, ys.max() + margin)))


model = AutoModelForImageTextToText.from_pretrained(M, dtype=torch.float16, attn_implementation="sdpa").to("cuda").eval()
proc = AutoProcessor.from_pretrained(M)


def run(img, prompt, new=900):
    msg = [{"role": "user", "content": [{"type": "image", "image": img}, {"type": "text", "text": prompt}]}]
    inp = proc.apply_chat_template(msg, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt").to("cuda")
    torch.cuda.synchronize(); t = time.time()
    with torch.no_grad():
        out = model.generate(**inp, max_new_tokens=new, do_sample=False, use_cache=True)
    torch.cuda.synchronize()
    return proc.decode(out[0][inp["input_ids"].shape[-1]:-1]), time.time() - t




def fit(img):
    """Thu nhỏ để số điểm ảnh <= MAX_PIXELS (transformers bản này bỏ qua size của processor)."""
    sc = (MAX_PIXELS / (img.width * img.height)) ** 0.5
    if sc >= 1:
        return img
    return img.resize((max(28, int(img.width * sc) // 28 * 28), max(28, int(img.height * sc) // 28 * 28)), Image.LANCZOS)


def blank(img):
    return (np.asarray(img.convert("L")) < 120).mean() < 0.002   # vùng gần như trắng thì bỏ qua


def ocr_split(page):
    """Cắt trang ở khung bảng: [phần trên | bảng | phần dưới], OCR từng phần rồi nối: dòng bảng nằm trên một dòng chữ."""
    box = find_table(page)
    if box is None:
        parts = [("trang", page)]
    else:
        x0, y0, x1, y1 = box
        parts = [("trên", page.crop((0, 0, page.width, y0))), ("bảng", page.crop(box)), ("dưới", page.crop((0, y1, page.width, page.height)))]
    texts, total = [], 0.0
    for name, img in parts:
        if blank(img):
            continue
        text, dt = run(fit(img), "OCR:", new=1200)
        total += dt
        print(f"    - {name}: {img.size} -> {dt:.1f}s", flush=True)
        texts.append(text.strip())
    return os.linesep.join(texts).replace("\r\n", "\n"), total, box


for png in sorted(Path("/scan").glob("*.png")):
    page = Image.open(png).convert("RGB")
    text, dt, box = ocr_split(page)
    (OUT / f"{png.stem}.txt").write_text(text, encoding="utf-8")
    print(f"== {png.name}: khung bảng {box}, tổng {dt:.1f}s", flush=True)
