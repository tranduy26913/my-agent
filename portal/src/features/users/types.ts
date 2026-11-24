/**
 * Hợp đồng của trang Tài khoản với backend (/api/admin/users, backend/app/api/admin_users.py). JSON camelCase.
 * Chỉ admin gọi được. Mọi thao tác ghi đều được backend ghi vào Nhật ký.
 *
 * Nguồn sự thật về "ai là nhân viên" là bảng employees; Zitadel chỉ giữ tài khoản đăng nhập. Mỗi dòng ghép hai bên theo email.
 */

/** none = nhân viên chưa có tài khoản; locked = Zitadel khoá tạm do nhập sai mật khẩu; other = trạng thái khác. */
export type AccountState = "active" | "inactive" | "locked" | "none" | "other";

export interface UserEmployee {
  code: string;
  department: string;
  title: string;
  roles: string[];
  /** Đang làm việc (không phải đã nghỉ việc) */
  active: boolean;
}

export interface AccountUser {
  /** id Zitadel nếu có tài khoản, không thì "e:<mã nhân viên>" */
  key: string;
  email: string;
  fullName: string;
  /** null = tài khoản Zitadel không có trong danh bạ nhân sự */
  employee: UserEmployee | null;
  /** null = chưa có tài khoản */
  zitadelId: string | null;
  account: AccountState;
  /** Câu cảnh báo khi hai bên lệch nhau (đã nghỉ việc mà tài khoản còn mở, tài khoản vô chủ...) */
  warning: string | null;
}

export interface CreatedAccount {
  user: AccountUser;
  /** Chỉ trả đúng một lần: backend không lưu và không ghi vào nhật ký */
  tempPassword: string;
}

export interface UsersApi {
  list(): Promise<AccountUser[]>;
  create(email: string): Promise<CreatedAccount>;
  deactivate(zitadelId: string): Promise<AccountUser>;
  reactivate(zitadelId: string): Promise<AccountUser>;
  /** Trả mật khẩu tạm (một lần). Người dùng bị buộc đổi ở lần đăng nhập sau. */
  resetPassword(zitadelId: string): Promise<string>;
}
