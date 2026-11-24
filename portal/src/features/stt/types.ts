/**
 * Hợp đồng của trang Ghi âm với backend (/api/stt, backend/app/api/stt.py, ADR-006). Backend trả snake_case;
 * `api/http.ts` đổi sang camelCase ở đây.
 *
 * Quyền riêng tư: backend xoá file ghi âm ngay khi xong, không lưu tên file. Chỉ văn bản kết quả được giữ (7 ngày, chỉ chủ job xem).
 */
export type JobStatus = "queued" | "running" | "done" | "failed";

/** Một đoạn lời nói, mốc thời gian tính bằng giây từ đầu file. */
export interface Segment {
  start: number;
  end: number;
  text: string;
  /** "A", "B", ... theo thứ tự xuất hiện; null = chưa phân biệt được người nói */
  speaker: string | null;
}

export interface SttJob {
  id: string;
  status: JobStatus;
  engine: string;
  language: string | null;
  /** 0 cho tới khi backend biết thời lượng (sau bước đổi định dạng). */
  durationS: number;
  doneS: number;
  error: string | null;
  createdAt: string;
  expiresAt: string;
}

export interface SttJobDetail extends SttJob {
  /** Chỉ có khi status = done */
  segments: Segment[] | null;
}

export interface SttEngines {
  default: string;
  engines: { name: string; available: boolean }[];
}

export interface SttApi {
  engines(): Promise<SttEngines>;
  /** Luôn bất đồng bộ: trả job ngay, lấy kết quả bằng getJob. */
  createJob(file: File, opts?: { language?: string }): Promise<SttJob>;
  listJobs(): Promise<SttJob[]>;
  getJob(id: string): Promise<SttJobDetail>;
  deleteJob(id: string): Promise<void>;
}
