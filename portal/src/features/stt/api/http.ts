import type { JobStatus, Segment, SttApi, SttEngines, SttJob } from "../types";

function errorMessage(raw: string, status: number): string {
  try {
    const detail = (JSON.parse(raw) as { detail?: unknown }).detail;
    if (typeof detail === "string" && detail) return detail;
    if (Array.isArray(detail)) {
      const msgs = detail.map((e) => (e as { msg?: string }).msg).filter(Boolean);
      if (msgs.length) return msgs.join("; ");
    }
  } catch {
    /* không phải JSON */
  }
  return raw || `Lỗi ${status}`;
}

interface RawJob {
  job_id: string;
  status: JobStatus;
  engine: string;
  language: string | null;
  duration_s: number;
  done_s: number;
  error: string | null;
  created_at: string;
  expires_at: string;
  segments?: Segment[] | null;
}

const toJob = (j: RawJob): SttJob => ({
  id: j.job_id,
  status: j.status,
  engine: j.engine,
  language: j.language,
  durationS: j.duration_s,
  doneS: j.done_s,
  error: j.error,
  createdAt: j.created_at,
  expiresAt: j.expires_at,
});

/** Bản cài gọi REST thật. `baseUrl` là gốc của nhóm stt, ví dụ "/api/stt" (đi qua BFF của portal). */
export function createHttpSttApi({ baseUrl }: { baseUrl: string }): SttApi {
  const base = baseUrl.replace(/\/$/, "");

  async function call(path: string, init: RequestInit = {}): Promise<Response> {
    let res: Response;
    try {
      res = await fetch(`${base}${path}`, { credentials: "same-origin", ...init });
    } catch {
      throw new Error("Mất kết nối mạng");
    }
    if (!res.ok) throw new Error(errorMessage(await res.text(), res.status));
    return res;
  }

  return {
    async engines() {
      return (await (await call("/engines")).json()) as SttEngines;
    },
    async createJob(file, opts) {
      const form = new FormData();
      form.append("file", file);
      const qs = opts?.language ? `?language=${encodeURIComponent(opts.language)}` : "";
      const res = await call(`/jobs${qs}`, { method: "POST", body: form });
      return toJob((await res.json()) as RawJob);
    },
    async listJobs() {
      return ((await (await call("/jobs")).json()) as RawJob[]).map(toJob);
    },
    async getJob(id) {
      const j = (await (await call(`/jobs/${encodeURIComponent(id)}`)).json()) as RawJob;
      return { ...toJob(j), segments: j.segments ?? null };
    },
    async deleteJob(id) {
      await call(`/jobs/${encodeURIComponent(id)}`, { method: "DELETE" });
    },
  };
}
