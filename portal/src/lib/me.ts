/**
 * Người dùng đang đăng nhập, như portal nhìn thấy. Dùng được ở cả server lẫn client.
 * Dựng từ phiên Zitadel và GET /api/me của backend (xem me.server.ts).
 */
export interface Me {
  name: string;
  email: string;
  /** Vai trò trong bảng employees của backend (ADR-004), ví dụ "admin", "manager", "employee". */
  roles: string[];
}

export const ROLE_ADMIN = "admin";

/** Không khai `roles` nghĩa là mọi người đều thấy. */
export function hasAnyRole(me: Me, roles?: readonly string[]): boolean {
  return !roles || roles.length === 0 || roles.some((r) => me.roles.includes(r));
}
