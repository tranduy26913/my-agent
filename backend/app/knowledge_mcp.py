"""knowledge-mcp: MCP server (streamable HTTP) cho LibreChat tra cứu kho tri thức SVT.

    python -m app.knowledge_mcp          # nghe ở 0.0.0.0:8100/mcp

Xác thực (docs/06 giai đoạn 4.3), thử theo thứ tự:
1. Authorization: Bearer <access token Zitadel> (đường đích); LibreChat điền
   {{LIBRECHAT_OPENID_ACCESS_TOKEN}};
   token được kiểm chữ ký/iss/aud rồi lấy email đã xác minh trong đó, không tin email do client tự khai.
2. TẠM (cờ KB_MCP_ALLOW_SHARED_TOKEN, mặc định bật đến khi chuyển xong, giai đoạn 6 xoá):
   X-KB-Token (bí mật dùng chung với LibreChat) + X-User-Email ({{LIBRECHAT_USER_EMAIL}}); chỉ tin email
   khi token đúng.
Có Bearer mà sai thì từ chối luôn, không lùi về đường 2. Sau khi có email, phòng ban/vai trò tra trong DB
(không nhận vai trò do client gửi). Không có gì hợp lệ -> từ chối hết (fail closed), kể cả khi chạy dev.
"""

import hmac
import logging
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
    # (vd vẫn dùng email/mật khẩu): coi như không có Bearer.
    if auth.lower().startswith("bearer ") and "{{" not in auth and auth[7:].strip():
        if verifier is None:
            raise PermissionError("knowledge-mcp: chưa cấu hình OIDC để kiểm Bearer token")
        try:
            return verifier.identity(auth[7:].strip()).email
        except OidcError as e:
            raise PermissionError(f"knowledge-mcp: {e}") from e
    if not settings.kb_mcp_allow_shared_token:
        raise PermissionError("knowledge-mcp: thiếu Bearer token")
    token = headers.get("x-kb-token", "")
    expected = settings.kb_mcp_token.encode()
    # So sánh bytes: compare_digest với str chỉ nhận ASCII, header chứa ký tự lạ sẽ thành lỗi 500.
    if not expected or not hmac.compare_digest(token.encode(), expected):
        raise PermissionError("knowledge-mcp: thiếu hoặc sai X-KB-Token")
    email = headers.get("x-user-email", "").strip()
    if not email or "{{" in email:  # placeholder chưa được LibreChat thay = cấu hình sai
        raise PermissionError("knowledge-mcp: không xác định được người dùng (X-User-Email)")
    return email


def _authenticate(ctx: Context) -> str:
    return authenticate_headers(dict(ctx.headers or {}), get_verifier())


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
