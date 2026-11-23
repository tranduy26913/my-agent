/**
 * Hợp đồng của trang Tra cứu với backend (POST /api/kb/ask, backend/app/api/ask.py).
 * JSON camelCase. Backend lọc tài liệu theo quyền của NGƯỜI ĐANG ĐĂNG NHẬP, không nhận vai trò từ client.
 */
export interface AskRequest {
  question: string;
  /** YYYY-MM-DD. Bỏ trống = hôm nay. Dùng khi hỏi quy định tại một thời điểm khác. */
  asOf?: string;
}

export interface Citation {
  /** Số [n] trong câu trả lời */
  n: number;
  /** Ví dụ "SVT-QC-003 – Điều 3: Số ngày phép" */
  label: string;
  docId: string | null;
}

export interface AskResult {
  answer: string;
  /** false = không tìm thấy trong tài liệu bạn được xem; `answer` là câu thông báo, không có nguồn */
  found: boolean;
  citations: Citation[];
  /** Vị trí tài liệu Mật bạn được xem nhưng trợ lý không đọc (SVT-CS-007 Điều 5) */
  withheld: string[];
  asOf: string;
  model: string;
  latencyMs: number;
}

export interface LookupApi {
  ask(req: AskRequest): Promise<AskResult>;
}
