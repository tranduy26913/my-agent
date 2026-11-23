"""Tool registry: định nghĩa tool, lọc theo quyền, thực thi an toàn.

Nguyên tắc:
1. Least privilege: model chỉ THẤY các tool user được phép dùng (lọc trước khi gửi).
2. Defense in depth: kiểm tra quyền lại lúc thực thi (model có thể "bịa" tên tool).
3. Lỗi tool không làm sập agent: trả về is_error=True để model tự sửa/thử cách khác.
4. Giới hạn kích thước output để không làm tràn context.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.security import UserInfo


@dataclass
class ToolContext:
    user: UserInfo
    db: Any = None  # sqlalchemy Session (None trong unit test)
    conversation_id: int | None = None


@dataclass
class ToolResult:
    content: str
    is_error: bool = False
    denied: bool = False  # bị chặn do phân quyền -> audit riêng


Handler = Callable[[ToolContext, dict], Any]


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    handler: Handler
    allowed_roles: set[str] | None = None  # None = mọi user
    source: str = "builtin"  # builtin | mcp:<server>
    strict: bool = True

    def to_api(self) -> dict:
        d = {"name": self.name, "description": self.description, "input_schema": self.input_schema}
        if self.strict:
            d["strict"] = True  # đảm bảo input khớp schema
        return d

    def permitted(self, user: UserInfo) -> bool:
        return self.allowed_roles is None or user.role in self.allowed_roles


def schema(properties: dict, required: list[str] | None = None) -> dict:
    """Helper tạo JSON Schema chuẩn cho strict tool use."""
    return {
        "type": "object",
        "properties": properties,
        "required": required if required is not None else list(properties),
        "additionalProperties": False,
    }


@dataclass
class ToolRegistry:
    max_output_chars: int = 8000
    _tools: dict[str, Tool] = field(default_factory=dict)

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool trùng tên: {tool.name}")
        self._tools[tool.name] = tool

    def names(self) -> list[str]:
        return list(self._tools)

    def for_user(self, user: UserInfo) -> list[Tool]:
        # Sắp xếp ổn định -> prefix prompt không đổi giữa các request -> prompt cache hit
        return [t for _, t in sorted(self._tools.items()) if t.permitted(user)]

    def execute(self, ctx: ToolContext, name: str, tool_input: dict) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(f"Tool '{name}' không tồn tại.", is_error=True)
        if not tool.permitted(ctx.user):
            return ToolResult(f"Bạn không có quyền dùng tool '{name}'.", is_error=True, denied=True)
        missing = [k for k in tool.input_schema.get("required", []) if k not in tool_input]
        if missing:
            return ToolResult(f"Thiếu tham số: {missing}", is_error=True)
        try:
            out = tool.handler(ctx, tool_input)
        except PermissionError as e:
            return ToolResult(f"Từ chối truy cập: {e}", is_error=True, denied=True)
        except Exception as e:  # noqa: BLE001 - trả lỗi cho model thay vì crash
            return ToolResult(f"Lỗi khi chạy tool {name}: {type(e).__name__}: {e}", is_error=True)
        text = out if isinstance(out, str) else json.dumps(out, ensure_ascii=False, default=str)
        if len(text) > self.max_output_chars:
            text = text[: self.max_output_chars] + "\n...[đã cắt bớt, hãy thu hẹp truy vấn]"
        return ToolResult(text)
