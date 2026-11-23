import type { Me } from "./me";

/**
 * Cách BFF xưng danh với FastAPI. Trình duyệt không bao giờ thấy các giá trị này (ADR-004).
 * Có hai kiểu, ứng với hai nhóm endpoint của backend:
 *
 *  - bearer: trang quản trị (/api/kb/*). Backend đòi JWT của một tài khoản admin.
 *  - asker : endpoint cho mọi nhân viên (/api/kb/ask). Backend đòi biết NGƯỜI ĐANG HỎI để lọc quyền xem tài liệu.
 *
 * TẠM, cả hai đều chờ Zitadel (docs/06, giai đoạn 4-5): sau này chỉ còn một kiểu là access token Zitadel
 * lấy từ phiên Auth.js, hai hàm dưới đây được thay bằng đọc phiên.
 */

/**
 * `API_DEV_TOKEN` trong `.env.local`, chỉ ở chế độ dev. Production luôn trả null nên BFF gọi backend không kèm
 * token và nhận 401, thay vì để mọi người dùng chung một token admin.
 */
export async function getBackendToken(): Promise<string | null> {
  if (process.env.NODE_ENV === "production") return null;
  return process.env.API_DEV_TOKEN || null;
}

/**
 * Bí mật dùng chung `PORTAL_BFF_TOKEN` (phải trùng với backend/.env) kèm email của người đang đăng nhập.
 * Backend chỉ tin email khi token đúng, rồi tự tra phòng ban và vai trò trong bảng employees.
 * Token này chỉ chứng minh "request đến từ BFF", không trao quyền admin nên không cần chặn ở production.
 */
export function getAskerHeaders(me: Me): Record<string, string> {
  const token = process.env.PORTAL_BFF_TOKEN;
  return token ? { "x-portal-token": token, "x-user-email": me.email } : {};
}
