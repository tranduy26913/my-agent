/**
 * Hợp đồng của trang Danh bạ với backend (GET /api/hr/directory, backend/app/api/hr.py, ADR-003). JSON camelCase.
 * Mọi nhân viên đang làm việc gọi được. Số điện thoại chỉ hiện với người cùng phòng (hoặc vai trò có quyền xem mọi số);
 * bị che thì `phone` là null và `phoneVisible` là false: tên, phòng, chức danh, email vẫn hiện.
 */

export interface DirectoryEntry {
  person: { code: string; name: string; department: string; title: string };
  email: string;
  /** null khi bị che, hoặc khi chưa có số */
  phone: string | null;
  /** false = bạn không có quyền xem số của người này (khác với chưa có số) */
  phoneVisible: boolean;
  /** false = đã nghỉ việc (chỉ Nhân sự thấy những người này) */
  active: boolean;
}

export interface Directory {
  items: DirectoryEntry[];
  /** Phòng ban của những người bạn được tra, không đổi theo bộ lọc phòng ban */
  departments: string[];
  /** true = còn người nữa: hãy thu hẹp bằng ô tìm kiếm */
  truncated: boolean;
}

export interface DirectoryQuery {
  /** Tên, email, chức danh hoặc mã; không phân biệt hoa thường và dấu */
  q: string;
  /** "" = tất cả */
  department: string;
}

export interface DirectoryApi {
  list(query: DirectoryQuery): Promise<Directory>;
}
