"""Engine `unlimited` (client SGLang/OpenAI-compatible) bằng server giả: không cần GPU hay model."""

import base64
import json

import httpx
import pytest
from PIL import Image

from app.config import settings
from app.ocr.engines import ENGINES, list_engines
from app.ocr.engines.unlimited import UnlimitedEngine, _clean


def engine_with(handler) -> UnlimitedEngine:
    return UnlimitedEngine(client=httpx.Client(transport=httpx.MockTransport(handler)))


@pytest.fixture(autouse=True)
def _url(monkeypatch):
    monkeypatch.setattr(settings, "ocr_sglang_url", "http://sglang.test:10000/")
    monkeypatch.setattr(settings, "ocr_sglang_api_key", "")
    monkeypatch.setattr(settings, "ocr_sglang_logit_processor", "")


def test_dang_ky_trong_engines():
    assert "unlimited" in ENGINES and "tesseract" in ENGINES


def test_chua_cau_hinh_url_thi_khong_san_sang(monkeypatch):
    monkeypatch.setattr(settings, "ocr_sglang_url", "")
    assert UnlimitedEngine().available() is False


def test_server_tat_thi_khong_san_sang():
    def down(request):
        raise httpx.ConnectError("refused")

    assert engine_with(down).available() is False


def test_san_sang_khi_models_tra_200():
    seen = {}

    def ok(request):
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"data": []})

    assert engine_with(ok).available() is True
    assert seen["url"] == "http://sglang.test:10000/v1/models"  # không có dấu // thừa


def test_server_loi_5xx_thi_khong_san_sang():
    assert engine_with(lambda r: httpx.Response(503)).available() is False


def test_goi_dung_giao_thuc_va_bo_token_dac_biet():
    seen = {}

    def reply(request):
        seen["body"] = json.loads(request.content)
        seen["path"] = request.url.path
        content = "<PAGE>Xin chào\n<｜end▁of▁sentence｜>"
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    text = engine_with(reply).recognize(Image.new("RGB", (40, 20), "white"), layout="rows")
    assert text == "Xin chào"
    assert seen["path"] == "/v1/chat/completions"
    b = seen["body"]
    assert b["model"] == settings.ocr_sglang_model and b["temperature"] == 0 and b["stream"] is False
    assert b["skip_special_tokens"] is False and b["images_config"] == {"crop_mode": True}
    image_part, text_part = b["messages"][0]["content"]
    prefix = "data:image/png;base64,"
    assert image_part["image_url"]["url"].startswith(prefix)
    assert base64.b64decode(image_part["image_url"]["url"][len(prefix):]).startswith(b"\x89PNG")
    assert text_part["text"] == settings.ocr_sglang_prompt
    assert "custom_logit_processor" not in b  # chưa cấu hình thì không gửi


def test_gui_logit_processor_va_api_key_khi_co_cau_hinh(monkeypatch):
    monkeypatch.setattr(settings, "ocr_sglang_logit_processor", "SERIALIZED")
    monkeypatch.setattr(settings, "ocr_sglang_api_key", "khoa-thu")
    seen = {}

    def reply(request):
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    engine_with(reply).recognize(Image.new("RGB", (8, 8)))
    assert seen["auth"] == "Bearer khoa-thu"
    assert seen["body"]["custom_logit_processor"] == "SERIALIZED"
    assert seen["body"]["custom_params"]["ngram_size"] == 35


def test_loi_http_nem_ngoai_le_de_service_doi_thanh_503_hoac_loi_engine():
    with pytest.raises(httpx.HTTPStatusError):
        engine_with(lambda r: httpx.Response(500, text="boom")).recognize(Image.new("RGB", (8, 8)))


def test_noi_dung_rong_tra_chuoi_rong():
    reply = lambda r: httpx.Response(200, json={"choices": [{"message": {"content": None}}]})  # noqa: E731
    assert engine_with(reply).recognize(Image.new("RGB", (8, 8))) == ""


def test_clean_giu_nguyen_chu_co_dau_ngoac_goc():
    assert _clean("Giá <5 triệu> và a<b") == "Giá <5 triệu> và a<b"
    assert _clean("<|im_end|>abc<PAGE>") == "abc"


def test_engines_list_khong_lam_hong_khi_unlimited_tat(monkeypatch):
    monkeypatch.setattr(settings, "ocr_sglang_url", "")
    names = {e["name"]: e["available"] for e in list_engines()}
    assert names["unlimited"] is False and "tesseract" in names
