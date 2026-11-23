import type { AccessCheck, KbApi, KbDocument, KbDocumentDetail, UploadMeta } from "../types";

/**
 * Bản cài gọi REST thật tới FastAPI. Hợp đồng endpoint (backend cần làm):
 *
 *   GET    {base}/documents                       → KbDocument[]
 *   GET    {base}/documents/{docId}               → KbDocumentDetail
 *   POST   {base}/documents          (multipart: file, meta?)  → KbDocument
 *   POST   {base}/documents:reindex  {docIds}   (204; 207 + {detail} nếu có tài liệu lỗi)
 *   PUT    {base}/documents/{docId}/quarantine  {on}
 *   POST   {base}/documents:delete   {docIds}
 *   GET    {base}/documents/{docId}/access?email=  → AccessCheck
 *
 * Xác thực do ứng dụng chủ lo: truyền `getHeaders` (Bearer) hoặc `credentials: "include"` (cookie).
 */
export interface HttpKbApiOptions {
  baseUrl: string;
  getHeaders?: () => Record<string, string> | Promise<Record<string, string>>;
  credentials?: RequestCredentials;
}

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

export function createHttpKbApi({ baseUrl, getHeaders, credentials }: HttpKbApiOptions): KbApi {
  const base = baseUrl.replace(/\/$/, "");

  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = { ...(init.body ? { "Content-Type": "application/json" } : {}), ...(await getHeaders?.()) };
    const res = await fetch(`${base}${path}`, { ...init, headers, credentials });
    if (!res.ok) throw new Error(errorMessage(await res.text(), res.status));
    // 207: thao tác hàng loạt xong nhưng có tài liệu lỗi; `detail` đã nêu rõ tài liệu nào và vì sao
    if (res.status === 207) throw new Error(((await res.json()) as { detail?: string }).detail ?? "Một số tài liệu bị lỗi");
    return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
  }

  const json = (body: unknown): RequestInit => ({ body: JSON.stringify(body) });

  return {
    listDocuments: () => request<KbDocument[]>("/documents"),
    getDocument: (id) => request<KbDocumentDetail>(`/documents/${encodeURIComponent(id)}`),
    reindex: (docIds) => request<void>("/documents:reindex", { method: "POST", ...json({ docIds }) }),
    setQuarantine: (id, on) => request<void>(`/documents/${encodeURIComponent(id)}/quarantine`, { method: "PUT", ...json({ on }) }),
    deleteDocuments: (docIds) => request<void>("/documents:delete", { method: "POST", ...json({ docIds }) }),
    checkAccess: (id, email) =>
      request<AccessCheck>(`/documents/${encodeURIComponent(id)}/access?email=${encodeURIComponent(email)}`),

    // fetch chưa báo được tiến độ tải lên nên dùng XMLHttpRequest
    async uploadDocument(file: File, meta: UploadMeta | null, onProgress) {
      const headers = (await getHeaders?.()) ?? {};
      return new Promise<KbDocument>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", `${base}/documents`);
        xhr.withCredentials = credentials === "include";
        Object.entries(headers).forEach(([k, v]) => xhr.setRequestHeader(k, v));
        xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(Math.round((e.loaded / e.total) * 100));
        xhr.onload = () =>
          xhr.status >= 200 && xhr.status < 300
            ? resolve(JSON.parse(xhr.responseText) as KbDocument)
            : reject(new Error(errorMessage(xhr.responseText, xhr.status)));
        xhr.onerror = () => reject(new Error("Mất kết nối mạng"));
        const form = new FormData();
        form.append("file", file);
        if (meta) form.append("meta", JSON.stringify(meta));
        xhr.send(form);
      });
    },
  };
}
