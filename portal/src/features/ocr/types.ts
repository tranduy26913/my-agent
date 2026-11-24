/**
 * Hợp đồng của trang OCR với backend (/api/ocr, backend/app/api/ocr.py, ADR-005). Backend trả snake_case;
 * `api/http.ts` đổi sang camelCase ở đây để phần còn lại của portal đồng nhất.
 *
 * Quyền riêng tư: backend không lưu file gốc và tên file. Chỉ job được lưu (văn bản kết quả, 7 ngày, chỉ chủ job xem).
 */
export type OcrSource = "text-layer" | "ocr";

export interface OcrPageResult {
  page: number;
  text: string;
  /** text-layer: PDF đã có chữ nhúng, không cần OCR; ocr: chữ nhận dạng từ ảnh */
  source: OcrSource;
  ms: number;
}

export interface OcrResult {
  engine: string;
  kind: "pdf" | "image";
  pages: OcrPageResult[];
  ocrPages: number;
  ms: number;
}

export type JobStatus = "queued" | "running" | "done" | "failed";

export interface OcrJob {
  id: string;
  status: JobStatus;
  engine: string;
  kind: "pdf" | "image" | null;
  pagesTotal: number;
  pagesDone: number;
  error: string | null;
  createdAt: string;
  expiresAt: string;
}

export interface OcrJobDetail extends OcrJob {
  /** Chỉ có khi status = done */
  pages: OcrPageResult[] | null;
  ocrPages: number | null;
}

export interface OcrOptions {
  /** Trang cần đọc, ví dụ "1,3-5". Bỏ trống = tất cả. */
  pages?: string;
}

export type Severity = "error" | "warning" | "info";

/** Một phát hiện khi kiểm tra phiếu. error = vi phạm/sai chắc chắn; warning = nghi ngờ, cần người xem; info = ghi chú. */
export interface Finding {
  code: string;
  severity: Severity;
  message: string;
  /** Vị trí trong phiếu, ví dụ "tong_cong" hoặc "cac_khoan[2]" */
  field: string | null;
  /** Điều khoản áp dụng, ví dụ "08/2025/QĐ-CTA Điều 5" */
  rule: string | null;
  /** Số tiền vượt định mức (đồng) */
  overAmount: number | null;
}

export type ExpenseKind = "phu_cap_luu_tru" | "khach_san" | "taxi" | "di_lai" | "tiep_khach" | "khac";

export interface ExpenseLine {
  content: string;
  /** Chép nguyên văn kèm đơn vị, ví dụ "2 đêm" */
  quantity: string;
  /** Đồng */
  amount: number;
  /** Cột hoá đơn đọc từ văn bản OCR: null = không đọc được hoặc phiếu ghi "-" */
  invoice: boolean | null;
  kind: ExpenseKind;
}

/** Giấy đề nghị thanh toán công tác phí (mẫu BM-CTP-03), sau khi đã chuẩn hoá. Tiền là đồng, ngày là YYYY-MM-DD. */
export interface ExpenseForm {
  formNo: string;
  employeeCode: string;
  fullName: string;
  department: string;
  place: string;
  fromDate: string;
  toDate: string;
  issuedDate: string;
  lines: ExpenseLine[];
  total: number;
  advance: number;
  payMore: number;
}

export interface ExtractResult {
  schemaId: string;
  form: ExpenseForm;
  findings: Finding[];
  /** true = cần người kiểm tra. Không bao giờ có nghĩa "đã duyệt": hệ thống không duyệt chi. */
  needsReview: boolean;
  engine: string;
  llmModel: string;
  pages: number;
  ocrPages: number;
  ms: number;
}

export interface OcrApi {
  /** Đồng bộ, một lần, không lưu. Dùng cho ảnh (một trang). */
  recognize(file: File, opts?: OcrOptions): Promise<OcrResult>;
  /** Bất đồng bộ: trả job ngay, kết quả lấy bằng getJob. Dùng cho PDF. */
  createJob(file: File, opts?: OcrOptions): Promise<OcrJob>;
  listJobs(): Promise<OcrJob[]>;
  getJob(id: string): Promise<OcrJobDetail>;
  deleteJob(id: string): Promise<void>;
  /** Đồng bộ (thường 7-13 giây): OCR, model chép ra JSON, đối chiếu và kiểm tra quy định. Không lưu kết quả. */
  extract(file: File, opts?: OcrOptions): Promise<ExtractResult>;
}
