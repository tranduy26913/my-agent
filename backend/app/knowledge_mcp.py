"""knowledge-mcp: MCP server (streamable HTTP) cho LibreChat tra cứu kho tri thức SVT.

    python -m app.knowledge_mcp          # nghe ở 0.0.0.0:8100/mcp

Xác thực (docs/06 giai đoạn 4.3): chỉ nhận `Authorization: Bearer <access token Zitadel>`; LibreChat điền
{{LIBRECHAT_OPENID_ACCESS_TOKEN}}. Token được kiểm chữ ký/iss/aud rồi lấy email đã xác minh trong đó, không
tin email do client tự khai. Sau khi có email, phòng ban/vai trò tra trong DB (không nhận từ client).
Không có token hợp lệ -> từ chối hết (fail closed), kể cả khi chạy dev. Đã gỡ X-KB-Token ở giai đoạn 6.
"""

import logging
import re
from datetime import date

import anyio
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from app.auth.oidc import OidcError, OidcVerifier, get_verifier
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


def authenticate_headers(headers: dict[str, str], verifier: OidcVerifier | None) -> str:
    """Email của người đang chat, hoặc PermissionError. Tách khỏi Context để test không cần dựng MCP."""
    headers = {k.lower(): v for k, v in headers.items()}
    auth = headers.get("authorization", "").strip()
    # "{{" (hoặc chuỗi rỗng sau "Bearer") = LibreChat chưa thay biến vì người dùng không đăng nhập bằng OIDC
    # (vd vẫn dùng email/mật khẩu): không có token để kiểm.
    if not auth.lower().startswith("bearer ") or "{{" in auth or not auth[7:].strip():
        raise PermissionError("knowledge-mcp: thiếu Bearer token (hãy đăng nhập LibreChat bằng Zitadel)")
    if verifier is None:
        raise PermissionError("knowledge-mcp: chưa cấu hình OIDC để kiểm Bearer token")
    try:
        return verifier.identity(auth[7:].strip()).email
    except OidcError as e:
        raise PermissionError(f"knowledge-mcp: {e}") from e


def _authenticate(ctx: Context) -> str:
    return authenticate_headers(dict(ctx.headers or {}), get_verifier())


_YEAR = re.compile(r"(?<!\d)(19|20)\d{2}(?!\d)")
# "12/3", "12-03-2025", "ngày 5 tháng 3", "tháng 3"
_DATE_HINT = re.compile(r"\d{1,2}\s*[/\-.]\s*\d{1,2}|ngày\s*\d{1,2}|tháng\s*\d{1,2}", re.IGNORECASE)


def usable_as_of(question: str, ref: date) -> bool:
    """Mô hình nhỏ hay tự điền as_of dù người dùng không nói gì (vd 2023-10-05) -> lọc hết tài liệu.
    Chỉ tin as_of khi chính câu hỏi nhắc năm trùng với as_of, hoặc có ngày/tháng cụ thể."""
    years = {int(m.group(0)) for m in _YEAR.finditer(question)}
    if years:
        return ref.year in years
    return bool(_DATE_HINT.search(question))


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
        if not usable_as_of(question, ref):
            log.info("bỏ as_of=%s do mô hình tự điền, câu hỏi không nhắc thời điểm: %r", as_of, question)
            ref = None
    # DB + embedding là code đồng bộ -> chạy trong thread để không chặn event loop của server
    return await anyio.to_thread.run_sync(_ask_sync, email, question, ref)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    if get_verifier() is None:
        log.warning("OIDC chưa cấu hình (OIDC_ISSUER, OIDC_PROJECT_ID): mọi request sẽ bị từ chối")
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
