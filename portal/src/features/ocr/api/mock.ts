import type { ExtractResult, OcrApi, OcrJob, OcrJobDetail, OcrPageResult } from "../types";

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

const SAMPLE =
  "CÔNG TY CỔ PHẦN SAO VIỆT\nGIẤY ĐỀ NGHỊ THANH TOÁN CÔNG TÁC PHÍ\nMã nhân viên: NV017\nĐi công tác: Đà Nẵng, 3 ngày\nTổng cộng: 4.250.000 đồng";

function pagesOf(n: number): OcrPageResult[] {
  return Array.from({ length: n }, (_, i) => ({
    page: i + 1,
    text: `${SAMPLE}\n(Trang ${i + 1} - dữ liệu giả)`,
    source: i % 2 === 0 ? ("ocr" as const) : ("text-layer" as const),
    ms: 900 + i * 120,
  }));
}

const SAMPLE_EXTRACT: ExtractResult = {
  schemaId: "cong-tac-phi",
  form: {
    formNo: "CTP-2026-0412",
    employeeCode: "NV018",
    fullName: "Phạm Thị Phương",
    department: "KD",
    place: "Đà Nẵng",
    fromDate: "2026-10-12",
    toDate: "2026-10-14",
    issuedDate: "2026-10-30",
    lines: [
      { content: "Vé máy bay khứ hồi", quantity: "1", amount: 3_450_000, invoice: true, kind: "di_lai" },
      { content: "Khách sạn (1.500.000 đ/đêm)", quantity: "2 đêm", amount: 3_000_000, invoice: true, kind: "khach_san" },
      { content: "Tiếp khách", quantity: "1", amount: 1_200_000, invoice: false, kind: "tiep_khach" },
    ],
    total: 7_650_000,
    advance: 5_000_000,
    payMore: 2_650_000,
  },
  findings: [
    { code: "khach_san_vuot_dinh_muc", severity: "error", message: "Khách sạn 1.500.000 đ/đêm vượt định mức 1.200.000 đ/đêm (vượt 600.000 đ cho 2 đêm)", field: "cac_khoan[1]", rule: "08/2025/QĐ-SVT Điều 5", overAmount: 600_000 },
    { code: "ngoai_danh_muc", severity: "error", message: "Khoản 'Tiếp khách' không thuộc danh mục công tác phí và không có hóa đơn", field: "cac_khoan[2]", rule: "08/2025/QĐ-SVT Điều 4, 5", overAmount: 1_200_000 },
    { code: "nguoi_duyet", severity: "info", message: "Tổng 7.650.000 đ: Kế toán trưởng phê duyệt", field: null, rule: "08/2025/QĐ-SVT Điều 8 khoản 2", overAmount: null },
  ],
  needsReview: true,
  engine: "mock",
  llmModel: "mock",
  pages: 1,
  ocrPages: 1,
  ms: 9000,
};

/** Dữ liệu giả để làm giao diện khi chưa có backend: job tiến triển theo thời gian thật (mỗi trang ~1 giây). */
export function createMockOcrApi(): OcrApi {
  const jobs = new Map<string, { job: OcrJob; startedAt: number; total: number }>();
  const PAGE_MS = 1000;

  function snapshot(id: string): OcrJob | undefined {
    const e = jobs.get(id);
    if (!e) return undefined;
    const done = Math.min(e.total, Math.floor((Date.now() - e.startedAt) / PAGE_MS));
    const status = done >= e.total ? "done" : done > 0 ? "running" : "queued";
    return { ...e.job, status, pagesDone: done, pagesTotal: e.total };
  }

  return {
    async recognize() {
      await sleep(1200);
      return { engine: "mock", kind: "image", pages: pagesOf(1), ocrPages: 1, ms: 1200 };
    },
    async createJob(file) {
      await sleep(400);
      const id = Math.random().toString(16).slice(2).padEnd(32, "0");
      const now = new Date();
      const total = Math.max(2, Math.min(8, Math.ceil(file.size / 200_000)));
      const job: OcrJob = {
        id,
        status: "queued",
        engine: "mock",
        kind: "pdf",
        pagesTotal: total,
        pagesDone: 0,
        error: null,
        createdAt: now.toISOString(),
        expiresAt: new Date(now.getTime() + 7 * 864e5).toISOString(),
      };
      jobs.set(id, { job, startedAt: Date.now(), total });
      return job;
    },
    async listJobs() {
      await sleep(150);
      return [...jobs.keys()]
        .map((id) => snapshot(id)!)
        .sort((a, b) => b.createdAt.localeCompare(a.createdAt));
    },
    async getJob(id): Promise<OcrJobDetail> {
      await sleep(150);
      const j = snapshot(id);
      if (!j) throw new Error("Không tìm thấy job");
      const done = j.status === "done";
      return { ...j, pages: done ? pagesOf(j.pagesTotal) : null, ocrPages: done ? Math.ceil(j.pagesTotal / 2) : null };
    },
    async deleteJob(id) {
      await sleep(150);
      jobs.delete(id);
    },
    async extract() {
      await sleep(1800);
      return SAMPLE_EXTRACT;
    },
  };
}
