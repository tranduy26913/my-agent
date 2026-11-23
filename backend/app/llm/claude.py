"""Adapter Claude API (Anthropic Python SDK)."""

import json

import anthropic

from app.llm.base import LLMResponse, ToolCall, Usage

FALLBACK_BETA = "server-side-fallback-2026-07-01"


class ClaudeClient:
    def __init__(self, model: str, effort: str = "medium", fallbacks: str = "default"):
        from app.config import settings

        self.model = model
        self.effort = effort
        self.fallbacks = fallbacks
        # SDK tự retry 408/409/429/5xx (mặc định 2 lần, exponential backoff)
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key or None, max_retries=3)

    def _create(self, **kwargs):
        # Prompt caching tự động: phần prefix (tools + system + lịch sử) được cache giữa các bước
        # của agent loop -> giảm mạnh chi phí input token.
        kwargs.setdefault("cache_control", {"type": "ephemeral"})
        if self.fallbacks:
            # Nếu model chính từ chối (stop_reason=refusal), server tự chạy lại trên model dự phòng.
            return self.client.beta.messages.create(
                betas=[FALLBACK_BETA], fallbacks=self.fallbacks, **kwargs
            )
        return self.client.messages.create(**kwargs)

    @staticmethod
    def _usage(resp) -> Usage:
        u = resp.usage
        return Usage(
            input_tokens=u.input_tokens or 0,
            output_tokens=u.output_tokens or 0,
            cache_read_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
            cache_write_tokens=getattr(u, "cache_creation_input_tokens", 0) or 0,
        )

    def complete(self, *, system, messages, tools, max_tokens=16000) -> LLMResponse:
        kwargs = dict(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            output_config={"effort": self.effort},
        )
        if tools:
            kwargs["tools"] = tools
        resp = self._create(**kwargs)
        text = "".join(b.text for b in resp.content if b.type == "text")
        calls = [ToolCall(b.id, b.name, b.input) for b in resp.content if b.type == "tool_use"]
        return LLMResponse(
            text=text,
            tool_calls=calls,
            stop_reason=resp.stop_reason,
            usage=self._usage(resp),
            model=resp.model,
            assistant_content=resp.content,
        )

    def complete_json(self, *, system, prompt, schema) -> tuple[dict, Usage]:
        resp = self._create(
            model=self.model,
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_config={
                "effort": "low",
                "format": {"type": "json_schema", "schema": schema},
            },
        )
        if resp.stop_reason == "refusal":
            raise RuntimeError("Model từ chối yêu cầu")
        text = next(b.text for b in resp.content if b.type == "text")
        return json.loads(text), self._usage(resp)
