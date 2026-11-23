"""Adapter model local (LocalAI / vLLM / Ollama) qua API tương thích OpenAI.

Chỉ hỗ trợ complete_json (đủ cho bước RAG). Agent loop cần tool-calling nên chưa dùng adapter này.
Dùng CÙNG một model với chat (vd qwen3-4b) -> không tốn thêm VRAM, trọng số chỉ nạp một lần.
"""

import json
import re

import httpx

from app.llm.base import LLMResponse, Usage

_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)


class LocalClient:
    def __init__(self, *, base_url: str, model: str, max_tokens: int = 700, timeout: float = 120.0,
                 api_key: str = "local") -> None:
        self.base_url = base_url.rstrip("/")
        # Tiền tố "local:" để observability tính chi phí 0 (không rơi vào giá mặc định của Opus).
        self.model = f"local:{model}"
        self._model = model
        self._max_tokens = max_tokens
        self._http = httpx.Client(timeout=timeout, headers={"Authorization": f"Bearer {api_key}"})

    def complete(
        self, *, system: str, messages: list[dict], tools: list[dict], max_tokens: int = 16000
    ) -> LLMResponse:
        raise NotImplementedError("LocalClient chỉ hỗ trợ complete_json (RAG), chưa có tool-calling")

    def complete_json(self, *, system: str, prompt: str, schema: dict) -> tuple[dict, Usage]:
        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                # "/no_think": Qwen3 bỏ chế độ suy nghĩ -> trả lời nhanh, không chèn <think> làm hỏng JSON.
                {"role": "user", "content": prompt + "\n\n/no_think"},
            ],
            "temperature": 0.1,
            "max_tokens": self._max_tokens,
            # Ép đầu ra đúng schema (LocalAI dựng grammar từ schema).
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "answer", "strict": True, "schema": schema},
            },
        }
        r = self._http.post(f"{self.base_url}/chat/completions", json=body)
        r.raise_for_status()
        data = r.json()
        text = _THINK.sub("", data["choices"][0]["message"]["content"] or "").strip()
        # Phòng khi model bọc JSON trong ```json ... ```
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
        u = data.get("usage") or {}
        return json.loads(text), Usage(
            input_tokens=u.get("prompt_tokens", 0), output_tokens=u.get("completion_tokens", 0)
        )
