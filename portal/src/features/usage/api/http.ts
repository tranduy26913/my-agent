import type { UsageApi, UsageReport } from "../types";

/** FastAPI trả lỗi dạng {"detail": "..."}: bóc ra câu để hiện cho người dùng. */
function errorMessage(raw: string, status: number): string {
  try {
    const detail = (JSON.parse(raw) as { detail?: unknown }).detail;
    if (typeof detail === "string" && detail) return detail;
  } catch {
    /* không phải JSON: dùng nguyên văn */
  }
  return raw || `Lỗi ${status}`;
}

/** Bản cài gọi REST thật. `baseUrl` là gốc của nhóm admin, ví dụ "/api/admin" (đi qua BFF của portal). */
export function createHttpUsageApi({ baseUrl }: { baseUrl: string }): UsageApi {
  const base = baseUrl.replace(/\/$/, "");
  return {
    async report(month?: string): Promise<UsageReport> {
      let res: Response;
      try {
        res = await fetch(`${base}/usage${month ? `?month=${encodeURIComponent(month)}` : ""}`, {
          credentials: "same-origin",
        });
      } catch {
        throw new Error("Mất kết nối mạng");
      }
      if (!res.ok) throw new Error(errorMessage(await res.text(), res.status));
      return (await res.json()) as UsageReport;
    },
  };
}
