import type { Segment, SttApi, SttJob, SttJobDetail } from "../types";

const LINES = [
  "Chào mọi người, chúng ta bắt đầu họp tiến độ dự án.",
  "Tuần này bên backend đã xong phần API nghỉ phép và danh bạ.",
  "Phần giao diện portal còn thiếu trang ghi âm cuộc họp.",
  "Anh Nam sẽ kiểm tra lại hạn mức upload qua proxy.",
  "Cuộc họp tiếp theo vào thứ Sáu tuần sau.",
];

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** Dữ liệu giả để làm giao diện khi chưa có backend: job dài 40 giây âm thanh, chạy 10 giây thật. */
export function createMockSttApi(): SttApi {
  const jobs = new Map<string, { job: SttJob; startedAt: number }>();
  const DURATION = 40;
  const RUN_MS = 10_000;
  const segments: Segment[] = LINES.map((text, i) => ({ start: i * 8, end: i * 8 + 7.5, text, speaker: i % 3 === 1 ? "B" : "A" }));

  function snapshot(id: string): SttJob | undefined {
    const e = jobs.get(id);
    if (!e) return undefined;
    const frac = Math.min(1, (Date.now() - e.startedAt) / RUN_MS);
    return { ...e.job, status: frac >= 1 ? "done" : "running", durationS: DURATION, doneS: Math.round(DURATION * frac) };
  }

  return {
    async engines() {
      await sleep(100);
      return { default: "mock", engines: [{ name: "mock", available: true }] };
    },
    async createJob() {
      await sleep(400);
      const id = crypto.randomUUID();
      const now = new Date();
      const job: SttJob = {
        id,
        status: "queued",
        engine: "mock",
        language: "vi",
        durationS: 0,
        doneS: 0,
        error: null,
        createdAt: now.toISOString(),
        expiresAt: new Date(now.getTime() + 7 * 864e5).toISOString(),
      };
      jobs.set(id, { job, startedAt: Date.now() });
      return job;
    },
    async listJobs() {
      return [...jobs.keys()].map((id) => snapshot(id)!).reverse();
    },
    async getJob(id): Promise<SttJobDetail> {
      const j = snapshot(id);
      if (!j) throw new Error("Không tìm thấy job");
      return { ...j, segments: j.status === "done" ? segments : null };
    },
    async deleteJob(id) {
      jobs.delete(id);
    },
  };
}
