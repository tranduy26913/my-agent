"""Hợp đồng chung cho mọi LLM provider.

Agent loop chỉ phụ thuộc vào interface này -> có thể thêm adapter cho model on-prem
(vLLM / Ollama) khi dữ liệu không được phép ra ngoài, mà không sửa agent.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    def __iadd__(self, other: "Usage") -> "Usage":
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.cache_read_tokens += other.cache_read_tokens
        self.cache_write_tokens += other.cache_write_tokens
        return self


@dataclass
class LLMResponse:
    text: str
    tool_calls: list[ToolCall]
    stop_reason: str  # end_turn | tool_use | max_tokens | pause_turn | refusal
    usage: Usage
    model: str
    # Nội dung assistant nguyên bản để append lại vào messages (giữ thinking blocks, không sửa)
    assistant_content: Any = field(default=None)


class LLMClient(Protocol):
    model: str

    def complete(
        self, *, system: str, messages: list[dict], tools: list[dict], max_tokens: int = 16000
    ) -> LLMResponse: ...

    def complete_json(self, *, system: str, prompt: str, schema: dict) -> tuple[dict, Usage]:
        """Structured output: trả về JSON đúng schema (dùng cho trích xuất, reflection...)."""
        ...
