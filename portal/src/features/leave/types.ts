/**
 * Hợp đồng của trang Nghỉ phép với backend (/api/hr/leave/*, backend/app/api/hr.py, ADR-003). JSON camelCase.
 * Chỉ đọc. Danh tính lấy từ phiên đăng nhập; không có tham số "xem của ai": phạm vi do backend quyết định theo vai trò.
 */

export interface Person {
  code: string;
  name: string;
  department: string;
  title: string;
}

export interface Balance {
  year: number;
  /** Phép năm được hưởng */
  entitled: number;
  /** Tồn chuyển sang từ năm trước */
  carriedOver: number;
  /** Tồn đã huỷ (quá hạn dùng) */
  carriedExpired: number;
  used: number;
  remaining: number;
}

/** cho-duyet | da-duyet | tu-choi; giá trị lạ vẫn hiện nguyên văn */
export type LeaveStatus = string;

export interface LeaveRequest {
  code: string;
  employee: Person;
  /** phep-nam, nghi-om-co-luong, ...; giá trị lạ vẫn hiện nguyên văn */
  kind: string;
  /** YYYY-MM-DD */
  fromDate: string;
  toDate: string;
  days: number;
  status: LeaveStatus;
  approverName: string | null;
  /** Lý do do nhân viên tự viết (dữ liệu cá nhân): chỉ người có quyền xem đơn mới thấy */
  note: string;
}

export interface MyLeave {
  year: number;
  person: Person;
  /** null = chưa có số liệu cho năm này */
  balance: Balance | null;
  requests: LeaveRequest[];
  /** Vai trò có phạm vi xem người khác: hiện tab "Nhóm của tôi" (backend vẫn tự kiểm quyền ở mỗi lần gọi) */
  canViewTeam: boolean;
}

export type Scope = "team" | "dept" | "all";

export interface Member {
  person: Person;
  balance: Balance | null;
  /** Số đơn đang chờ duyệt */
  pending: number;
}

export interface TeamLeave {
  year: number;
  scopes: Scope[];
  members: Member[];
  requests: LeaveRequest[];
}

export interface LeaveApi {
  me(): Promise<MyLeave>;
  /** Mỗi lần gọi backend ghi một dòng Nhật ký (xem dữ liệu của người khác): chỉ gọi khi người dùng mở tab. */
  team(): Promise<TeamLeave>;
}
