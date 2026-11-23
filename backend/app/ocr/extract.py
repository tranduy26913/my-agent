# ruff: noqa: E501  (docstring và thông báo tiếng Việt; cắt dòng làm khó đọc)
"""Trích xuất có cấu trúc: ảnh/PDF -> OCR -> LLM chép ra JSON -> chuẩn hóa -> đối chiếu OCR -> kiểm tra quy định.

Vai trò của từng bước và vì sao (ADR-005 mục 8):
- OCR: app.ocr.service (engine + tiền xử lý đã chọn theo số đo).
- LLM: CHỈ chép dữ liệu theo schema. Đầu ra bị ép đúng schema (LocalAI dựng grammar) nhưng vẫn coi là KHÔNG đáng tin.
- Mã tất định (app/ocr/schemas/*): chuẩn hóa, đối chiếu từng con số với văn bản OCR, kiểm tra số học và quy định.
  Việc duyệt chi vẫn do người: kết quả chỉ nói `needs_review`, không bao giờ nói "duyệt".

Riêng tư: văn bản OCR đi tới LLM của LLM_PROVIDER. `local` (mặc định demo) thì dữ liệu không rời máy;
`claude` thì rời máy -> chỉ dùng cho tài liệu không thuộc diện Mật (SVT-CS-007 Điều 5).
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from app.config import settings
from app.llm.base import Usage
from app.ocr import service
from app.ocr.errors import EngineFailed, EngineUnavailable, NoTextFound
from app.ocr.schemas import get_schema
from app.ocr.schemas.base import EmployeeInfo, ExtractContext, Finding

log = logging.getLogger("ocr.extract")


@dataclass
class ExtractResult:
    schema_id: str
    data: dict
    findings: list[Finding]
    needs_review: bool
    engine: str
    kind: str
    pages: int
    ocr_pages: int
    llm_model: str
    usage: Usage = field(default_factory=Usage)
    ms: int = 0


def get_extract_llm():
    """LLM cho trích xuất theo LLM_PROVIDER. `fake` không có chế độ JSON có nghĩa nên không dùng được."""
    provider = settings.llm_provider
    if provider == "local":
        from app.llm.local import LocalClient

        return LocalClient(
            base_url=settings.local_llm_base_url, model=settings.local_llm_model,
            max_tokens=settings.ocr_extract_max_tokens, timeout=settings.local_llm_timeout,
        )
    if provider == "claude":
        from app.llm.claude import ClaudeClient

        return ClaudeClient(model=settings.anthropic_small_model, fallbacks=settings.llm_fallbacks)
    raise EngineUnavailable(f"LLM_PROVIDER={provider!r} không hỗ trợ trích xuất; dùng local hoặc claude")


def _wrap(text: str) -> str:
    """Đặt văn bản OCR trong thẻ phân định; chặn việc văn bản tự đóng thẻ để thoát ra thành "chỉ dẫn"."""
    safe = text.replace("</ocr>", "< /ocr>").replace("<ocr>", "< ocr>")
    return f"<ocr>\n{safe}\n</ocr>"


def extract(
    data: bytes,
    schema_id: str,
    *,
    engine: str | None = None,
    pages: str | None = None,
    employee_lookup: Callable[[str], EmployeeInfo | None] | None = None,
    llm=None,
) -> ExtractResult:
    schema = get_schema(schema_id)
    t0 = time.perf_counter()

    ocr = service.recognize(data, engine=engine, pages=pages, layout=schema.ocr_layout)
    text = "\n\n".join(p.text for p in ocr.pages).strip()
    if not text:
        raise NoTextFound("OCR không đọc ra chữ nào trong tài liệu")
    truncated = len(text) > settings.ocr_extract_max_chars
    text = text[: settings.ocr_extract_max_chars]

    llm = llm or get_extract_llm()
    try:
        raw, usage = llm.complete_json(system=schema.system_prompt, prompt=_wrap(text), schema=schema.json_schema)
    except Exception as e:  # noqa: BLE001 - mạng, model, JSON hỏng... người dùng chỉ cần biết là thất bại
        log.exception("Trích xuất %s: LLM lỗi", schema_id)
        raise EngineFailed("Trích xuất thất bại: model không trả được dữ liệu hợp lệ") from e
    try:
        parsed = schema.parse(raw, text)
    except ValueError as e:
        raise EngineFailed(str(e)) from e

    ctx = ExtractContext()
    code = schema.employee_code_of(parsed)
    if code and employee_lookup:
        ctx = ExtractContext(employee=employee_lookup(code), employee_lookup_done=True)
    findings = schema.validate(parsed, text, ctx)
    if truncated:
        findings.append(Finding("van_ban_bi_cat", "warning",
                                f"Văn bản OCR dài hơn {settings.ocr_extract_max_chars} ký tự, phần sau bị cắt"))
    return ExtractResult(
        schema_id=schema.id, data=parsed, findings=findings,
        needs_review=any(f.severity in ("error", "warning") for f in findings),
        engine=ocr.engine, kind=ocr.kind, pages=len(ocr.pages), ocr_pages=ocr.ocr_pages,
        llm_model=llm.model, usage=usage, ms=int((time.perf_counter() - t0) * 1000),
    )
