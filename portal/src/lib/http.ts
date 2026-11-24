/**
 * Gọi API của backend qua BFF (cùng origin, cookie phiên đi kèm) và đổi lỗi thành câu tiếng Việt để hiện cho người dùng.
 * Mô-đun trong src/features được import file này (không dính Next): chỉ dùng fetch chuẩn.
 */

/** FastAPI trả lỗi dạng {"detail": "..."} (hoặc mảng lỗi kiểm tra dữ liệu): bóc ra câu để hiện. */
export function errorMessage(raw: string, status: number): string {
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

/** fetch + kiểm tra mã trả về. Ném Error có câu dùng được; 204 trả undefined. */
export async function apiJson<T>(url: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, { credentials: "same-origin", ...init });
  } catch {
    throw new Error("Mất kết nối mạng");
  }
  if (!res.ok) throw new Error(errorMessage(await res.text(), res.status));
  return (res.status === 204 ? undefined : await res.json()) as T;
}

export function postJson<T>(url: string, body?: unknown): Promise<T> {
  return apiJson<T>(url, {
    method: "POST",
    headers: body === undefined ? undefined : { "content-type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}
