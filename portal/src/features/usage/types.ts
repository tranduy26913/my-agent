/**
 * Hợp đồng của trang Chi phí với backend (GET /api/admin/usage, backend/app/api/admin.py). JSON camelCase.
 * Chỉ admin gọi được. Tổng hợp từ bảng usage_logs theo tháng (UTC).
 */
export interface UsageGroup {
  /** Khoá ổn định của nhóm; với nhóm "theo người" là "e12" (nhân viên) hoặc "u5" (tài khoản cũ) */
  key: string;
  name: string;
  /** Phòng ban (chỉ có ở nhóm theo người) */
  department: string;
  calls: number;
  inputTokens: number;
  outputTokens: number;
  costUsd: number;
}

export interface UsageReport {
  /** YYYY-MM */
  month: string;
  /** Các tháng có dữ liệu, tăng dần */
  months: string[];
  calls: number;
  inputTokens: number;
  outputTokens: number;
  costUsd: number;
  /** Ngân sách mỗi người mỗi tháng (USD), để so với chi phí từng người */
  budgetUsdPerUser: number;
  byUser: UsageGroup[];
  byModel: UsageGroup[];
  byPurpose: UsageGroup[];
  /** name = YYYY-MM-DD */
  byDay: UsageGroup[];
}

export interface UsageApi {
  /** month bỏ trống = tháng hiện tại */
  report(month?: string): Promise<UsageReport>;
}
