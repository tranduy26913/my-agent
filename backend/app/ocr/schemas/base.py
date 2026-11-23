# ruff: noqa: E501  (chú thích tiếng Việt)
"""Hợp đồng chung của một "schema trích xuất" (ADR-005 mục 8)."""

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class EmployeeInfo:
    """Thông tin tối thiểu về người lập phiếu để áp quy định; tra từ bảng employees theo mã NV."""

    code: str
    full_name: str
    truong_phong_tro_len: bool  # roles có truong-phong hoặc executive -> định mức khách sạn +30%
    active: bool = True


@dataclass
class Finding:
    """Một phát hiện. severity: error = vi phạm/sai chắc chắn; warning = nghi ngờ, cần người xem; info = ghi chú."""

    code: str
    severity: str  # error | warning | info
    message: str
    field: str | None = None
    rule: str | None = None  # điều khoản áp dụng, vd "08/2025/QĐ-SVT Điều 5"
    over_amount: int | None = None  # số tiền vượt định mức (đồng), nếu có


@dataclass
class ExtractContext:
    employee: EmployeeInfo | None = None
    employee_lookup_done: bool = False  # True = đã tra bảng employees (dù có thấy hay không)


@dataclass
class ExtractSchema:
    id: str
    title: str
    description: str
    json_schema: dict  # schema ép đầu ra của LLM (phẳng, không $ref để LocalAI dựng được grammar)
    system_prompt: str
    parse: Callable[[dict, str], dict]  # (JSON thô của LLM, văn bản OCR) -> dữ liệu chuẩn hóa (ValueError nếu sai)
    validate: Callable[[dict, str, ExtractContext], list[Finding]]  # (dữ liệu, văn bản OCR, ngữ cảnh) -> phát hiện
    employee_code_of: Callable[[dict], str | None] = field(default=lambda _d: None)
    ocr_layout: str | None = None  # gợi ý bố cục cho engine OCR (xem OcrEngine.recognize)
