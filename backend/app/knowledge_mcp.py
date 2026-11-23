"""knowledge-mcp: MCP server (streamable HTTP) cho LibreChat tra cứu kho tri thức SVT.

    python -m app.knowledge_mcp          # nghe ở 0.0.0.0:8100/mcp

Xác thực 2 lớp:
1. X-KB-Token  : bí mật dùng chung với LibreChat -> chứng minh request đến từ LibreChat.
2. X-User-Email: LibreChat điền {{LIBRECHAT_USER_EMAIL}} của người đang chat. CHỈ tin header này khi
   token đúng; sau đó tra phòng ban/vai trò trong DB (không nhận vai trò do client gửi).
Không có token đúng -> từ chối hết (fail closed), kể cả khi chạy dev.
"""

import hmac
import logging
from datetime import date

import anyio
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from app.config import settings
from app.db import SessionLocal
from app.rag.acl import load_principal
from app.rag.answer import ask

log = logging.getLogger("knowledge-mcp")

mcp = MCPServer(
    name="knowledge-mcp",
    instructions=(
        "Tra cứu quy chế, quy trình, chính sách, hướng dẫn nội bộ của Công ty Sao Việt (SVT). "
        "Kết quả đã được lọc theo quyền của người đang chat và kèm trích dẫn nguồn."
    ),
)


def _authenticate(ctx: Context) -> str:
    headers = {k.lower(): v for k, v in (ctx.headers or {}).items()}
    token = headers.get("x-kb-token", "")
    if not settings.kb_mcp_token or not hmac.compare_digest(token, settings.kb_mcp_token):
        raise PermissionError("knowledge-mcp: thiếu hoặc sai X-KB-Token")
    email = headers.get("x-user-email", "").strip()
    if not email or "{{" in email:  # placeholder chưa được LibreChat thay = cấu hình sai
        raise PermissionError("knowledge-mcp: không xác định được người dùng (X-User-Email)")
    return email


def _ask_sync(email: str, question: str, as_of: date | None) -> str:
    with SessionLocal() as db:
        p = load_principal(db, email)
        if p is None:
            return "Tài khoản của bạn chưa có trong danh bạ nhân sự SVT nên không tra cứu được tài liệu."
        if not p.active:
            return "Tài khoản nhân sự của bạn không còn hoạt động nên không tra cứu được tài liệu nội bộ."
        return ask(db, question, p, as_of=as_of).render()


@mcp.tool()
async def ask_knowledge(question: str, ctx: Context, as_of: str | None = None) -> str:
    """Trả lời câu hỏi về quy định nội bộ SVT: nghỉ phép, nội quy, giờ làm việc, lương thưởng, công tác phí,
    mua sắm – thanh toán, tuyển dụng, CNTT, an toàn thông tin, dự án... Câu trả lời đã có trích dẫn [n] và
    danh sách nguồn: hãy giữ nguyên trích dẫn và nguồn khi trình bày lại cho người dùng, không thêm thông tin
    ngoài kết quả này. Nếu kết quả nói không tìm thấy, hãy nói đúng như vậy, không trả lời từ kiến thức chung.

    Args:
        question: câu hỏi đầy đủ, viết lại rõ nghĩa nếu đang hỏi tiếp câu trước (vd "còn nghỉ ốm thì sao?"
            -> "Quy định nghỉ ốm như thế nào?").
        as_of: ngày tham chiếu YYYY-MM-DD, CHỈ điền khi người dùng hỏi về quy định tại một thời điểm khác
            hôm nay (vd "năm 2024 được mấy ngày phép" -> "2024-06-30"). Bỏ trống trong mọi trường hợp khác.
    """
    try:
        email = _authenticate(ctx)
    except PermissionError as e:
        log.warning("%s", e)
        return f"Từ chối truy cập: {e}"
    ref = None
    if as_of:
        try:
            ref = date.fromisoformat(as_of)
        except ValueError:
            return "as_of phải có dạng YYYY-MM-DD."
    # DB + embedding là code đồng bộ -> chạy trong thread để không chặn event loop của server
    return await anyio.to_thread.run_sync(_ask_sync, email, question, ref)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    if not settings.kb_mcp_token:
        log.warning("KB_MCP_TOKEN chưa đặt: mọi request sẽ bị từ chối")
    # Chống DNS rebinding: chỉ nhận Host là localhost hoặc host.docker.internal (LibreChat trong Docker).
    security = TransportSecuritySettings(
        allowed_hosts=["127.0.0.1:*", "localhost:*", "host.docker.internal:*"],
        allowed_origins=["http://127.0.0.1:*", "http://localhost:*"],
    )
    mcp.run(
        transport="streamable-http", host=settings.kb_mcp_host, port=settings.kb_mcp_port,
        transport_security=security, stateless_http=True,
    )


if __name__ == "__main__":
    main()
