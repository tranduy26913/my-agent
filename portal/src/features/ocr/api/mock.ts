import type { OcrApi, OcrJob, OcrJobDetail, OcrPageResult } from "../types";

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
  };
}
