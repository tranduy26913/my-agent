import type {
  ExpenseKind,
  ExpenseLine,
  ExtractResult,
  Finding,
  JobStatus,
  OcrApi,
  OcrJob,
  OcrJobDetail,
  OcrOptions,
  OcrPageResult,
  OcrResult,
} from "../types";

/** OCR một ảnh mất vài giây đến vài chục giây; quá lâu thì báo lỗi thay vì chờ mãi. */
const SYNC_TIMEOUT_MS = 180_000;

/** FastAPI trả lỗi dạng {"detail": "..."} (hoặc mảng lỗi kiểm tra dữ liệu): bóc ra câu để hiện cho người dùng. */
function errorMessage(raw: string, status: number): string {
  try {
    const detail = (JSON.parse(raw) as { detail?: unknown }).detail;
    if (typeof detail === "string" && detail) return detail;
    if (Array.isArray(detail)) {
      const msgs = detail.map((e) => (e as { msg?: string }).msg).filter(Boolean);
      if (msgs.length) return msgs.join("; ");
    }
  } catch {
    /* không phải JSON: dùng nguyên văn */
  }
  return raw || `Lỗi ${status}`;
}

interface RawPage {
  page: number;
  text: string;
  source: "text-layer" | "ocr";
  ms: number;
}

interface RawJob {
  job_id: string;
  status: JobStatus;
  engine: string;
  kind: "pdf" | "image" | null;
  pages_total: number;
  pages_done: number;
  error: string | null;
  created_at: string;
  expires_at: string;
  pages?: RawPage[] | null;
  ocr_pages?: number | null;
}

interface RawExtract {
  schema_id: string;
  data: {
    so_phieu: string;
    ma_nv: string;
    ho_ten: string;
    phong_ban: string;
    noi_cong_tac: string;
    tu_ngay: string;
    den_ngay: string;
    ngay_lap: string;
    cac_khoan: { noi_dung: string; so_luong: string; thanh_tien: number; co_hoa_don: boolean | null; loai: ExpenseKind }[];
    tong_cong: number;
    da_tam_ung: number;
    de_nghi_thanh_toan_them: number;
  };
  findings: { code: string; severity: Finding["severity"]; message: string; field: string | null; rule: string | null; over_amount: number | null }[];
  needs_review: boolean;
  engine: string;
  llm_model: string;
  pages: number;
  ocr_pages: number;
  ms: number;
}

const toExtract = (r: RawExtract): ExtractResult => ({
  schemaId: r.schema_id,
  form: {
    formNo: r.data.so_phieu,
    employeeCode: r.data.ma_nv,
    fullName: r.data.ho_ten,
    department: r.data.phong_ban,
    place: r.data.noi_cong_tac,
    fromDate: r.data.tu_ngay,
    toDate: r.data.den_ngay,
    issuedDate: r.data.ngay_lap,
    lines: r.data.cac_khoan.map(
      (l): ExpenseLine => ({ content: l.noi_dung, quantity: l.so_luong, amount: l.thanh_tien, invoice: l.co_hoa_don, kind: l.loai }),
    ),
    total: r.data.tong_cong,
    advance: r.data.da_tam_ung,
    payMore: r.data.de_nghi_thanh_toan_them,
  },
  findings: r.findings.map((f) => ({ code: f.code, severity: f.severity, message: f.message, field: f.field, rule: f.rule, overAmount: f.over_amount })),
  needsReview: r.needs_review,
  engine: r.engine,
  llmModel: r.llm_model,
  pages: r.pages,
  ocrPages: r.ocr_pages,
  ms: r.ms,
});

const toPage = (p: RawPage): OcrPageResult => ({ page: p.page, text: p.text, source: p.source, ms: p.ms });

const toJob = (j: RawJob): OcrJob => ({
  id: j.job_id,
  status: j.status,
  engine: j.engine,
  kind: j.kind,
  pagesTotal: j.pages_total,
  pagesDone: j.pages_done,
  error: j.error,
  createdAt: j.created_at,
  expiresAt: j.expires_at,
});

const toDetail = (j: RawJob): OcrJobDetail => ({
  ...toJob(j),
  pages: j.pages ? j.pages.map(toPage) : null,
  ocrPages: j.ocr_pages ?? null,
});

/** Bản cài gọi REST thật. `baseUrl` là gốc của nhóm ocr, ví dụ "/api/ocr" (đi qua BFF của portal). */
export function createHttpOcrApi({ baseUrl }: { baseUrl: string }): OcrApi {
  const base = baseUrl.replace(/\/$/, "");

  async function call(path: string, init: RequestInit = {}): Promise<Response> {
    let res: Response;
    try {
      res = await fetch(`${base}${path}`, { credentials: "same-origin", ...init });
    } catch (e) {
      if (e instanceof DOMException && e.name === "TimeoutError") {
        throw new Error("Xử lý quá lâu. Hãy thử file nhỏ hơn, hoặc gửi PDF để chạy nền.");
      }
      throw new Error("Mất kết nối mạng");
    }
    if (!res.ok) throw new Error(errorMessage(await res.text(), res.status));
    return res;
  }

  function upload(path: string, file: File, opts?: OcrOptions, init: RequestInit = {}) {
    const params = new URLSearchParams();
    if (opts?.pages?.trim()) params.set("pages", opts.pages.trim());
    const form = new FormData();
    form.append("file", file);
    const qs = params.toString();
    return call(`${path}${qs ? `?${qs}` : ""}`, { method: "POST", body: form, ...init });
  }

  return {
    async recognize(file, opts) {
      const res = await upload("/recognize", file, opts, { signal: AbortSignal.timeout(SYNC_TIMEOUT_MS) });
      const r = (await res.json()) as {
        engine: string;
        kind: "pdf" | "image";
        pages: RawPage[];
        ocr_pages: number;
        ms: number;
      };
      return { engine: r.engine, kind: r.kind, pages: r.pages.map(toPage), ocrPages: r.ocr_pages, ms: r.ms } satisfies OcrResult;
    },
    async createJob(file, opts) {
      return toJob((await (await upload("/jobs", file, opts)).json()) as RawJob);
    },
    async listJobs() {
      return ((await (await call("/jobs")).json()) as RawJob[]).map(toJob);
    },
    async getJob(id) {
      return toDetail((await (await call(`/jobs/${encodeURIComponent(id)}`)).json()) as RawJob);
    },
    async extract(file, opts) {
      const res = await upload("/extract", file, opts, { signal: AbortSignal.timeout(SYNC_TIMEOUT_MS) });
      return toExtract((await res.json()) as RawExtract);
    },
    async deleteJob(id) {
      await call(`/jobs/${encodeURIComponent(id)}`, { method: "DELETE" });
    },
  };
}
