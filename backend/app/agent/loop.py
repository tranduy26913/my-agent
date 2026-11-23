"""Agent loop tự viết (không dùng framework) - phần cốt lõi nên hiểu sâu khi phỏng vấn.

    user msg ─► LLM ─► có tool_use? ──không──► trả lời
                 ▲          │ có
                 │          ▼
                 └── tool_result ◄── thực thi tool (check quyền, audit, giới hạn output)

Viết tay thay vì SDK tool runner / LangGraph để kiểm soát: RBAC từng lần gọi, audit từng bước,
ngân sách chi phí, giới hạn số bước, xử lý refusal/pause_turn.
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import ToolContext, ToolRegistry
from app.llm.base import LLMClient, Usage
from app.observability import AuditSink, cost_usd


@dataclass
class AgentResult:
    answer: str
    stop: str  # done | max_steps | refusal | budget_exceeded | max_tokens
    steps: list[dict] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    model: str = ""

    @property
    def cost_usd(self) -> float:
        return cost_usd(self.model, self.usage)


class AgentRunner:
    def __init__(
        self,
        llm: LLMClient,
        registry: ToolRegistry,
        audit: AuditSink,
        max_steps: int = 8,
        budget_ok: Callable[[], bool] | None = None,
        system_prompt: str = SYSTEM_PROMPT,
    ):
        self.llm, self.registry, self.audit = llm, registry, audit
        self.max_steps = max_steps
        self.budget_ok = budget_ok or (lambda: True)
        self.system_prompt = system_prompt

    def run(self, ctx: ToolContext, user_turn: str, history: list[dict] | None = None) -> AgentResult:
        # Bộ tool cố định trong suốt 1 lượt chạy (không thêm/bớt giữa chừng -> giữ prefix & cache)
        tools = self.registry.for_user(ctx.user)
        tool_defs = [t.to_api() for t in tools]
        messages: list[dict] = list(history or []) + [{"role": "user", "content": user_turn}]
        result = AgentResult(answer="", stop="done", model=self.llm.model)

        for step in range(self.max_steps):
            if not self.budget_ok():
                self.audit.log("budget_exceeded", {"step": step})
                result.answer, result.stop = "Bạn đã dùng hết ngân sách AI tháng này.", "budget_exceeded"
                return result

            resp = self.llm.complete(system=self.system_prompt, messages=messages, tools=tool_defs)
            result.usage += resp.usage
            result.model = resp.model
            self.audit.log("llm_call", {
                "step": step, "stop_reason": resp.stop_reason, "model": resp.model,
                "input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens,
                "cache_read": resp.usage.cache_read_tokens,
                "tool_calls": [c.name for c in resp.tool_calls],
            })

            if resp.stop_reason == "refusal":
                self.audit.log("refusal", {"step": step})
                result.answer, result.stop = "Xin lỗi, tôi không thể hỗ trợ yêu cầu này.", "refusal"
                return result

            # Luôn append nguyên văn nội dung assistant (append-only, không chỉnh sửa lịch sử)
            messages.append({"role": "assistant", "content": resp.assistant_content})

            if resp.stop_reason == "pause_turn":
                continue  # server tool đang chạy dài -> gửi lại để tiếp tục
            if resp.stop_reason == "max_tokens" and not resp.tool_calls:
                result.answer, result.stop = resp.text + "\n…(bị cắt do giới hạn độ dài)", "max_tokens"
                return result
            if not resp.tool_calls:
                result.answer = resp.text
                return result

            # Thực thi tool. Tất cả tool_result trả về trong MỘT user message (hỗ trợ parallel tool use).
            tool_results: list[dict] = []
            for call in resp.tool_calls:
                r = self.registry.execute(ctx, call.name, call.input)
                event = "tool_denied" if r.denied else "tool_call"
                self.audit.log(event, {
                    "step": step, "tool": call.name, "input": call.input,
                    "is_error": r.is_error, "output_preview": r.content[:300],
                })
                result.steps.append({"tool": call.name, "input": call.input,
                                     "is_error": r.is_error, "output_preview": r.content[:300]})
                tool_results.append({
                    "type": "tool_result", "tool_use_id": call.id,
                    "content": r.content, "is_error": r.is_error,
                })
            if step == self.max_steps - 2:
                # Sắp hết số bước: nhắc model chốt câu trả lời ở lượt kế tiếp
                tool_results.append({"type": "text", "text": "Bạn sắp hết số bước cho phép. "
                                     "Hãy tổng hợp và trả lời người dùng ngay, không gọi thêm tool."})
            messages.append({"role": "user", "content": tool_results})

        result.answer = "Nhiệm vụ quá phức tạp, đã đạt giới hạn số bước. Hãy chia nhỏ yêu cầu."
        result.stop = "max_steps"
        return result
