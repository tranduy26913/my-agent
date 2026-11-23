"""Các hàm đo của app/ocr/eval.py (thuần Python, không cần Tesseract)."""

import unicodedata
from pathlib import Path

import pytest

from app.ocr.eval import (
    cer,
    edit_distance,
    field_hits,
    form_checks,
    load_ground_truth,
    normalize,
    strip_accents,
    wer,
)

GT_PATH = Path(__file__).resolve().parents[2] / "data" / "scan" / "ground-truth.md"


def test_edit_distance():
    assert edit_distance("kitten", "sitting") == 3
    assert edit_distance("", "abc") == 3
    assert edit_distance(["a", "b"], ["a", "c"]) == 1


def test_cer_wer_co_ban():
    assert cer("giờ làm việc", "giờ làm việc") == 0
    assert cer("abcd", "abxd") == pytest.approx(0.25)
    assert wer("một hai ba bốn", "một hai bay bốn") == pytest.approx(0.25)
    assert cer("", "") == 0 and cer("", "rác") == 1


def test_cer_bo_qua_khac_biet_khoang_trang_va_unicode_dung_san_to_hop():
    ref = "Điều 3:\n   Giờ  làm việc"
    hyp = unicodedata.normalize("NFD", "Điều 3: Giờ làm việc")
    assert cer(ref, hyp) == 0


def test_strip_accents_ke_ca_chu_d():
    assert strip_accents("Đà Nẵng, đường Hồ Thị Phương") == "Da Nang, duong Ho Thi Phuong"


def test_tach_loi_dau_khoi_loi_ky_tu():
    ref = "Công ty thông báo"
    hyp = "Cong ty thong bao"  # đúng chữ, mất hết dấu
    assert cer(ref, hyp) > 0.1
    assert cer(strip_accents(ref), strip_accents(hyp)) == 0


def test_doc_ground_truth_that():
    gt = load_ground_truth(GT_PATH)
    assert gt.tb018_text.startswith("CÔNG TY CỔ PHẦN CÔNG NGHỆ SAO VIỆT")
    assert "Phạm Đức Long" in gt.tb018_text
    assert set(gt.forms) == {"NV017", "NV018"}
    assert gt.forms["NV018"]["tong_cong"] == 15180000


def test_truong_can_tim_cua_phieu():
    form = load_ground_truth(GT_PATH).forms["NV017"]
    names = [n for n, _, _ in form_checks(form)]
    assert {"so_phieu", "ho_ten", "tong_cong", "khoan1.thanh_tien", "khoan4.thanh_tien"} <= set(names)


def test_field_hits_dau_phan_cach_va_dau_tieng_viet():
    form = load_ground_truth(GT_PATH).forms["NV017"]
    ocr = "Số phiếu CTP-2026-0412  Ma NV: NV017  Ho ten: Le Van Binh  Tong cong 7,270,000  Tam ung 5.000.000"
    hits = field_hits(form, ocr)
    assert hits["so_phieu"] == {"strict": True, "loose": True}
    assert hits["ho_ten"] == {"strict": False, "loose": True}  # mất dấu: chỉ đạt khi bỏ dấu
    assert hits["tong_cong"]["strict"] and hits["da_tam_ung"]["strict"]  # cả dấu phẩy lẫn dấu chấm
    assert not hits["khoan1.thanh_tien"]["loose"]  # 3450000 không có trong văn bản


def test_so_tien_khong_khop_nham_mot_phan_cua_so_dai_hon():
    form = {"so_phieu": "A", "ma_nv": "B", "ho_ten": "C", "phong_ban": "D", "noi_cong_tac": "E",
            "cac_khoan": [], "tong_cong": 900000, "da_tam_ung": 0, "de_nghi_thanh_toan_them": 0}
    assert not field_hits(form, "tổng 1.900.000")["tong_cong"]["loose"]
    assert field_hits(form, "tổng 900.000")["tong_cong"]["loose"]


def test_normalize():
    assert normalize("  a \n\n b\t c ") == "a b c"
