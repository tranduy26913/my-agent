import type { AuditApi, AuditPage, AuditQuery } from "../types";

const PAGE_SIZE = 50;

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

/** Bản cài gọi REST thật. `baseUrl` là gốc của nhóm admin, ví dụ "/api/admin" (đi qua BFF của portal). */
export function createHttpAuditApi({ baseUrl }: { baseUrl: string }): AuditApi {
  const base = baseUrl.replace(/\/$/, "");
  return {
    async list(q: AuditQuery, cursor?: number | null): Promise<AuditPage> {
      const params = new URLSearchParams({ limit: String(PAGE_SIZE) });
      if (q.event) params.set("event", q.event);
      if (q.actor.trim()) params.set("actor", q.actor.trim());
      if (q.since) params.set("since", q.since);
      if (q.until) params.set("until", q.until);
      if (cursor) params.set("beforeId", String(cursor));
      let res: Response;
      try {
        res = await fetch(`${base}/audit?${params}`, { credentials: "same-origin" });
      } catch {
        throw new Error("Mất kết nối mạng");
      }
      if (!res.ok) throw new Error(errorMessage(await res.text(), res.status));
      return (await res.json()) as AuditPage;
    },
  };
}
