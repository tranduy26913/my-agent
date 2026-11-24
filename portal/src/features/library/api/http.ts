import { apiJson } from "@/lib/http";
import type { Library, LibraryApi, LibraryQuery } from "../types";

/** Bản cài gọi REST thật. `baseUrl` là gốc của nhóm kb, ví dụ "/api/kb" (đi qua BFF của portal). */
export function createHttpLibraryApi({ baseUrl }: { baseUrl: string }): LibraryApi {
  const base = baseUrl.replace(/\/$/, "");
  return {
    list(query: LibraryQuery) {
      const params = new URLSearchParams();
      if (query.type) params.set("type", query.type);
      if (query.department) params.set("department", query.department);
      if (query.status) params.set("status", query.status);
      if (query.q.trim()) params.set("q", query.q.trim());
      const qs = params.toString();
      return apiJson<Library>(`${base}/library${qs ? `?${qs}` : ""}`);
    },
  };
}
