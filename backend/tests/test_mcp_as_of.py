"""as_of do mô hình nhỏ tự điền không được làm lọc mất tài liệu (audit 2063, 2026-11-24)."""

from datetime import date

import pytest

from app.knowledge_mcp import usable_as_of


@pytest.mark.parametrize("question", [
    "quy định nghỉ phép",
    "Nhân viên chính thức được nghỉ phép bao nhiêu ngày?",
    "còn nghỉ ốm thì sao?",
    "quy định về công tác phí trong văn bản CTA-QC-003",  # mã văn bản có số nhưng không phải năm
])
def test_cau_hoi_khong_nhac_thoi_diem_thi_bo_as_of(question):
    assert not usable_as_of(question, date(2023, 10, 5))


@pytest.mark.parametrize("question, ref", [
    ("năm 2024 được mấy ngày phép", date(2024, 6, 30)),
    ("Quy chế áp dụng từ năm 2025 như thế nào", date(2025, 1, 1)),
    ("ngày 15/03 quy định giờ làm việc ra sao", date(2024, 3, 15)),
    ("tháng 3 năm ngoái nghỉ phép thế nào", date(2025, 3, 1)),
    ("ngày 5 tháng 3 có được nghỉ không", date(2024, 3, 5)),
])
def test_cau_hoi_co_thoi_diem_thi_giu_as_of(question, ref):
    assert usable_as_of(question, ref)


def test_nam_trong_cau_hoi_khac_as_of_thi_bo():
    # Người dùng hỏi năm 2024 nhưng mô hình điền 2023: không tin
    assert not usable_as_of("năm 2024 được mấy ngày phép", date(2023, 6, 30))
