"""LLM giả lập để test và demo offline (không tốn tiền, không cần API key)."""

import itertools
import json

from app.llm.base import LLMResponse, ToolCall, Usage

_ids = itertools.count(1)


def _assistant_blocks(text: str, calls: list[ToolCall]) -> list[dict]:
    blocks: list[dict] = [{"type": "text", "text": text}] if text else []
    blocks += [{"type": "tool_use", "id": c.id, "name": c.name, "input": c.input} for c in calls]
    return blocks


def make_response(text: str = "", calls: list[ToolCall] | None = None) -> LLMResponse:
    calls = calls or []
    return LLMResponse(
        text=text,
        tool_calls=calls,
        stop_reason="tool_use" if calls else "end_turn",
        usage=Usage(input_tokens=100, output_tokens=20),
        model="fake",
        assistant_content=_assistant_blocks(text, calls),
    )


class ScriptedLLM:
    """Trả lời theo kịch bản định sẵn -> unit test agent loop một cách tất định."""

    model = "fake"

    def __init__(self, responses: list[LLMResponse], json_responses: list[dict] | None = None):
        self.responses = list(responses)
        self.json_responses = list(json_responses or [])
        self.calls: list[dict] = []

    def complete(self, *, system, messages, tools, max_tokens=16000) -> LLMResponse:
        self.calls.append({"system": system, "messages": list(messages), "tools": tools})
        return self.responses.pop(0)

    def complete_json(self, *, system, prompt, schema):
        return self.json_responses.pop(0), Usage()


class RuleBasedFakeLLM:
    """Demo offline: luôn tra kho tri thức trước, sau đó trả lời bằng kết quả tool."""

    model = "fake"

    def complete(self, *, system, messages, tools, max_tokens=16000) -> LLMResponse:
        last = messages[-1]["content"]
        tool_names = {t["name"] for t in tools}
        if isinstance(last, str) and "search_knowledge" in tool_names:
            question = last.split("Câu hỏi của người dùng:")[-1].strip()
            call = ToolCall(f"toolu_fake_{next(_ids)}", "search_knowledge", {"query": question, "top_k": 3})
            return make_response("Mình sẽ tra cứu kho tri thức.", [call])
        if isinstance(last, list):
            results = [b.get("content", "") for b in last if b.get("type") == "tool_result"]
            return make_response("[Chế độ FAKE LLM] Kết quả tra cứu:\n\n" + "\n\n".join(results)[:1500])
        return make_response("[Chế độ FAKE LLM] Xin chào! Hãy đặt LLM_PROVIDER=claude để dùng model thật.")

    def complete_json(self, *, system, prompt, schema):
        # Trả JSON rỗng hợp lệ tối thiểu theo các field required
        out = {}
        for key, spec in schema.get("properties", {}).items():
            t = spec.get("type")
            out[key] = {"string": "", "boolean": False, "array": [], "integer": 0, "number": 0}.get(
                t if isinstance(t, str) else "string", None
            )
        return json.loads(json.dumps(out)), Usage()
