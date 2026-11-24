import { apiJson } from "@/lib/http";
import type { Directory, DirectoryApi, DirectoryQuery } from "../types";

/** Bản cài gọi REST thật. `baseUrl` là gốc của nhóm hr, ví dụ "/api/hr" (đi qua BFF của portal). */
export function createHttpDirectoryApi({ baseUrl }: { baseUrl: string }): DirectoryApi {
  const base = baseUrl.replace(/\/$/, "");
  return {
    list(query: DirectoryQuery) {
      const params = new URLSearchParams();
      if (query.q.trim()) params.set("q", query.q.trim());
      if (query.department) params.set("department", query.department);
      const qs = params.toString();
      return apiJson<Directory>(`${base}/directory${qs ? `?${qs}` : ""}`);
    },
  };
}
