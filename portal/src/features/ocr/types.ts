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

export interface OcrApi {
  /** Đồng bộ, một lần, không lưu. Dùng cho ảnh (một trang). */
  recognize(file: File, opts?: OcrOptions): Promise<OcrResult>;
  /** Bất đồng bộ: trả job ngay, kết quả lấy bằng getJob. Dùng cho PDF. */
  createJob(file: File, opts?: OcrOptions): Promise<OcrJob>;
  listJobs(): Promise<OcrJob[]>;
  getJob(id: string): Promise<OcrJobDetail>;
  deleteJob(id: string): Promise<void>;
}
