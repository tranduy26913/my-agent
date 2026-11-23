"""Đo chất lượng OCR trên data/scan/ so với đáp án trong data/scan/ground-truth.md (ADR-005, mục 3).

    python -m app.ocr.eval                       # đo engine mặc định
    python -m app.ocr.eval --engines tesseract   # chọn engine (nhiều engine: cách nhau bằng dấu phẩy)

Hai loại phép đo, vì ground-truth.md có hai loại đáp án:
1. Văn bản thông báo SVT-TB-018 (PNG và PDF scan): có đáp án TỪNG CHỮ -> đo CER và WER.
   Đo cả bản "bỏ dấu" để tách lỗi DẤU (ạ/ả/ã...) khỏi lỗi KÝ TỰ: CER(có dấu) cao mà CER(bỏ dấu) thấp
   nghĩa là engine đọc đúng chữ nhưng sai dấu - lỗi rất hay gặp ở tiếng Việt.
2. Phiếu đề nghị thanh toán NV017/NV018: đáp án là JSON, không phải văn bản thô -> đo tỉ lệ TRƯỜNG ĐÚNG
   (số phiếu, mã NV, họ tên, nơi công tác, các số tiền) có xuất hiện trong văn bản OCR không.

Bản OCR thô được lưu ở data/eval/reports/ocr-raw/ để xem tận mắt engine sai ở đâu.
"""

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

SCAN_DIR = Path("../data/scan")
REPORT_DIR = Path("../data/eval/reports")
TB018 = ("SVT-TB-018-dieu-chinh-gio-lam-viec.png", "SVT-TB-018-dieu-chinh-gio-lam-viec.pdf")


# ---------- chuẩn hóa và đo khoảng cách ----------

def strip_accents(s: str) -> str:
    """Bỏ dấu tiếng Việt. 'đ' không tách được bằng NFD nên phải đổi riêng."""
    s = s.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def normalize(s: str) -> str:
    """NFC + gộp mọi khoảng trắng/xuống dòng thành một dấu cách (đáp án có thụt lề, gạch đầu dòng...)."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip()


def edit_distance(a, b) -> int:
    """Levenshtein (thêm/xóa/thay đều tính 1). Dùng được cho chuỗi ký tự lẫn danh sách từ."""
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def cer(ref: str, hyp: str) -> float:
    """Character Error Rate = số lỗi ký tự / độ dài đáp án. Có thể > 1 nếu OCR sinh nhiều rác."""
    ref, hyp = normalize(ref), normalize(hyp)
    if not ref:
        return 0.0 if not hyp else 1.0
    return edit_distance(ref, hyp) / len(ref)


def wer(ref: str, hyp: str) -> float:
    r, h = normalize(ref).split(), normalize(hyp).split()
    if not r:
        return 0.0 if not h else 1.0
    return edit_distance(r, h) / len(r)


# ---------- đáp án ----------

@dataclass
class GroundTruth:
    tb018_text: str
    forms: dict[str, dict] = field(default_factory=dict)  # mã NV -> JSON đáp án


def load_ground_truth(path: Path) -> GroundTruth:
    md = path.read_text(encoding="utf-8")
    blocks = re.findall(r"```(\w*)\n(.*?)```", md, re.S)
    texts = [body for lang, body in blocks if lang == "text"]
    if not texts:
        raise ValueError("ground-truth.md: không thấy khối ```text của SVT-TB-018")
    gt = GroundTruth(tb018_text=texts[0].strip())
    for lang, body in blocks:
        if lang == "json":
            form = json.loads(body)
            gt.forms[form["ma_nv"]] = form
    return gt


def form_checks(form: dict) -> list[tuple[str, str, str]]:
    """Các trường cần tìm thấy trong văn bản OCR: [(tên, loại 'text'|'money', giá trị)]."""
    checks = [(k, "text", str(form[k])) for k in ("so_phieu", "ma_nv", "ho_ten", "phong_ban", "noi_cong_tac")]
    for i, item in enumerate(form.get("cac_khoan", []), 1):
        checks.append((f"khoan{i}.thanh_tien", "money", str(item["thanh_tien"])))
    for k in ("tong_cong", "da_tam_ung", "de_nghi_thanh_toan_them"):
        checks.append((k, "money", str(form[k])))
    return checks


def _join_digit_groups(text: str) -> str:
    """'3.450.000' hoặc '3,450,000' -> '3450000' để so với số trong đáp án."""
    return re.sub(r"(?<=\d)[.,](?=\d)", "", text)


def field_hits(form: dict, ocr_text: str) -> dict[str, dict[str, bool]]:
    """Mỗi trường có 2 kết quả: strict = đúng cả dấu và hoa/thường; loose = bỏ dấu, bỏ hoa/thường."""
    text = normalize(ocr_text)
    loose = strip_accents(text).casefold()
    digits = _join_digit_groups(text)
    out = {}
    for name, kind, value in form_checks(form):
        if kind == "money":
            ok = bool(re.search(rf"(?<!\d){re.escape(value)}(?!\d)", digits))
            out[name] = {"strict": ok, "loose": ok}
        else:
            out[name] = {
                "strict": normalize(value) in text,
                "loose": strip_accents(normalize(value)).casefold() in loose,
            }
    return out


# ---------- chạy đo ----------

@dataclass
class TextRow:
    file: str
    cer: float
    cer_no_accent: float
    wer: float
    ms: int


@dataclass
class FormRow:
    file: str
    strict: int
    loose: int
    total: int
    missed: list[str]
    ms: int


def run_engine(engine: str, scan_dir: Path, gt: GroundTruth, raw_dir: Path | None = None):
    from app.ocr import service

    def ocr(name: str):
        res = service.recognize((scan_dir / name).read_bytes(), engine=engine)
        text = "\n\n".join(p.text for p in res.pages)
        if raw_dir:
            raw_dir.mkdir(parents=True, exist_ok=True)
            (raw_dir / f"{date.today()}-{engine}-{Path(name).stem}.txt").write_text(text, encoding="utf-8")
        return text, res

    text_rows, form_rows = [], []
    for name in TB018:
        text, res = ocr(name)
        text_rows.append(TextRow(
            name, cer(gt.tb018_text, text),
            cer(strip_accents(gt.tb018_text), strip_accents(text)),
            wer(gt.tb018_text, text), res.ms,
        ))
    for ma_nv, form in sorted(gt.forms.items()):
        name = f"de-nghi-thanh-toan-CTP-{ma_nv}.png"
        text, res = ocr(name)
        hits = field_hits(form, text)
        form_rows.append(FormRow(
            name, sum(h["strict"] for h in hits.values()), sum(h["loose"] for h in hits.values()),
            len(hits), [k for k, h in hits.items() if not h["loose"]], res.ms,
        ))
    return text_rows, form_rows


def render_report(results: dict[str, tuple[list[TextRow], list[FormRow]]]) -> str:
    out = [f"# Đo chất lượng OCR ({date.today()})", "",
           "Nguồn đáp án: `data/scan/ground-truth.md`. CER/WER càng thấp càng tốt; "
           "trường đúng càng cao càng tốt.", ""]
    for engine, (texts, forms) in results.items():
        out += [f"## Engine `{engine}`", "", "### Văn bản thông báo SVT-TB-018", "",
                "| File | CER | CER (bỏ dấu) | WER | Thời gian |", "|---|---|---|---|---|"]
        out += [
            f"| {r.file} | {r.cer:.1%} | {r.cer_no_accent:.1%} | {r.wer:.1%} | {r.ms} ms |"
            for r in texts
        ]
        out += ["", "### Phiếu đề nghị thanh toán (trường đúng)", "",
                "| File | Đúng cả dấu | Đúng (bỏ dấu) | Thời gian | Trường không tìm thấy |",
                "|---|---|---|---|---|"]
        out += [
            f"| {r.file} | {r.strict}/{r.total} | {r.loose}/{r.total} | {r.ms} ms "
            f"| {', '.join(r.missed) or '-'} |"
            for r in forms
        ]
        out.append("")
    return "\n".join(out)


def main() -> None:
    from app.config import settings

    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Đo chất lượng OCR trên data/scan")
    ap.add_argument("--engines", default=settings.ocr_engine, help="tên engine, cách nhau bằng dấu phẩy")
    ap.add_argument("--scan-dir", default=str(SCAN_DIR))
    args = ap.parse_args()

    scan_dir = Path(args.scan_dir)
    gt = load_ground_truth(scan_dir / "ground-truth.md")
    results = {e: run_engine(e, scan_dir, gt, REPORT_DIR / "ocr-raw") for e in args.engines.split(",")}
    report = render_report(results)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / f"{date.today()}-ocr.md"
    out.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nĐã ghi {out}")


if __name__ == "__main__":
    main()
