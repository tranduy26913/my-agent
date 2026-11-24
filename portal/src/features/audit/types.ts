/**
 * Hợp đồng của trang Nhật ký với backend (GET /api/admin/audit, backend/app/api/admin.py). JSON camelCase.
 * Chỉ admin gọi được. Backend KHÔNG trả nội dung nhạy cảm (câu hỏi của nhân viên, tham số và kết quả của tool):
 * `detail` đã được lọc theo danh sách trắng của từng sự kiện.
 */

/** alert = cần chú ý ngay (xem tài liệu Mật, công cụ bị từ chối); warn = đáng xem lại. */
export type Highlight = "alert" | "warn" | null;

export interface AuditItem {
  id: number;
  /** ISO 8601 */
  ts: string;
  /** Mã sự kiện, ví dụ "kb_view_classified" */
  event: string;
  /** Email hoặc tên người thực hiện; "hệ thống" nếu không có */
  actor: string;
  /** Nhãn tiếng Việt của sự kiện */
  label: string;
  summary: string;
  highlight: Highlight;
  detail: Record<string, unknown>;
}

export interface AuditQuery {
  /** Mã sự kiện; "" = tất cả */
  event: string;
  /** Một phần email hoặc tên */
  actor: string;
  /** YYYY-MM-DD, "" = không giới hạn */
  since: string;
  until: string;
}

export interface AuditPage {
  items: AuditItem[];
  /** Truyền lại làm `cursor` để lấy trang cũ hơn; null = hết */
  nextCursor: number | null;
  /** Số dòng của từng loại sự kiện trong TOÀN BỘ bảng (để dựng bộ lọc) */
  eventCounts: Record<string, number>;
  eventLabels: Record<string, string>;
}

export interface AuditApi {
  list(query: AuditQuery, cursor?: number | null): Promise<AuditPage>;
}
