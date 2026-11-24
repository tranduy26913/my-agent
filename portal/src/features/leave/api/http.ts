import { apiJson } from "@/lib/http";
import type { LeaveApi, MyLeave, TeamLeave } from "../types";

/** Bản cài gọi REST thật. `baseUrl` là gốc của nhóm hr, ví dụ "/api/hr" (đi qua BFF của portal). */
export function createHttpLeaveApi({ baseUrl }: { baseUrl: string }): LeaveApi {
  const base = baseUrl.replace(/\/$/, "");
  return {
    me: () => apiJson<MyLeave>(`${base}/leave/me`),
    team: () => apiJson<TeamLeave>(`${base}/leave/team`),
  };
}
