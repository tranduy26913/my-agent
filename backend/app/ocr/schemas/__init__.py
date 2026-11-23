"""Sổ đăng ký schema trích xuất. Thêm loại tài liệu mới = thêm một module + một dòng ở đây."""

from app.ocr.errors import OcrError
from app.ocr.schemas import cong_tac_phi
from app.ocr.schemas.base import ExtractSchema

SCHEMAS: dict[str, ExtractSchema] = {s.id: s for s in (cong_tac_phi.SCHEMA,)}


class UnknownSchema(OcrError):
    status_code = 404


def get_schema(schema_id: str) -> ExtractSchema:
    if schema_id not in SCHEMAS:
        raise UnknownSchema(f"Không có schema {schema_id!r}. Có: {', '.join(sorted(SCHEMAS))}")
    return SCHEMAS[schema_id]
