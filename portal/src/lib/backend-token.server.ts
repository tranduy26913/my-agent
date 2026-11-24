import "server-only";
import type { Me } from "./me";

/**
 * Cách BFF xưng danh với FastAPI. Trình duyệt không bao giờ thấy các giá trị này (ADR-004).
 *
 * Đường chính (đã đăng nhập Zitadel): BFF gắn `Authorization: Bearer <access token của người dùng>` lấy từ phiên
 * (lib/me.server.ts), xem src/app/api/[...path]/route.ts. Hai hàm dưới đây CHỈ dùng khi PORTAL_DEV_AUTH=1 (người
 * dùng giả, không có token thật) và sẽ bị xoá ở giai đoạn 6 cùng cầu nối tương ứng ở backend (docs/06).
 */

/** `API_DEV_TOKEN` trong `.env.local`: JWT HS256 cũ của tài khoản admin trong bảng users. */
export function getDevBackendToken(): string | null {
  return process.env.API_DEV_TOKEN || null;
}

/** Bí mật dùng chung `PORTAL_BFF_TOKEN` (trùng backend/.env) kèm email người dùng giả. */
export function getDevAskerHeaders(me: Me): Record<string, string> {
  const token = process.env.PORTAL_BFF_TOKEN;
  return token ? { "x-portal-token": token, "x-user-email": me.email } : {};
}
