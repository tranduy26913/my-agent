"""Cấu hình dùng chung cho mọi test.

Test không được phụ thuộc backend/.env của người chạy: máy demo đặt OCR_ENGINE=paddleocr_vl kèm server OCR và
engine dự phòng, nhưng test cần engine giả và hành vi "engine tắt thì 503" mặc định.
"""

import pytest

from app.config import settings


@pytest.fixture(autouse=True)
def _ocr_settings_khong_phu_thuoc_env(monkeypatch):
    monkeypatch.setattr(settings, "ocr_engine", "tesseract")
    monkeypatch.setattr(settings, "ocr_fallback_engine", "")
    monkeypatch.setattr(settings, "ocr_paddlevl_url", "")
    monkeypatch.setattr(settings, "ocr_sglang_url", "")
