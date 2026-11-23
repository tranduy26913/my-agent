/**
 * Người dùng đang đăng nhập, như portal nhìn thấy. Dùng được ở cả server lẫn client.
 * Hiện là dữ liệu giả (xem me.server.ts). Khi có Zitadel, `getMe()` đọc từ phiên thật, kiểu này giữ nguyên.
 */
export interface Me {
  name: string;
  email: string;
  /** Project role của Zitadel, ví dụ "admin", "nhan-vien". */
  roles: string[];
}

export const ROLE_ADMIN = "admin";

/** Không khai `roles` nghĩa là mọi người đều thấy. */
export function hasAnyRole(me: Me, roles?: readonly string[]): boolean {
  return !roles || roles.length === 0 || roles.some((r) => me.roles.includes(r));
}
