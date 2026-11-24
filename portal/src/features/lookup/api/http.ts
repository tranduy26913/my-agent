import type { AskRequest, AskResult, LookupApi } from "../types";

/** Model local trả lời mất vài chục giây, nhưng quá lâu thì báo lỗi thay vì để người dùng chờ mãi. */
const TIMEOUT_MS = 150_000;

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

/** Bản cài gọi REST thật. `baseUrl` là gốc của nhóm kb, ví dụ "/api/kb" (đi qua BFF của portal). */
export function createHttpLookupApi({ baseUrl }: { baseUrl: string }): LookupApi {
  const base = baseUrl.replace(/\/$/, "");
  return {
    async ask(req: AskRequest) {
      let res: Response;
      try {
        res = await fetch(`${base}/ask`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(req),
          credentials: "same-origin",
          signal: AbortSignal.timeout(TIMEOUT_MS),
        });
      } catch (e) {
        if (e instanceof DOMException && e.name === "TimeoutError") {
          throw new Error("Trợ lý phản hồi quá lâu. Hãy thử lại sau hoặc hỏi ngắn gọn hơn.");
        }
        throw new Error("Mất kết nối mạng");
      }
      if (!res.ok) throw new Error(errorMessage(await res.text(), res.status));
      return (await res.json()) as AskResult;
    },
  };
}
