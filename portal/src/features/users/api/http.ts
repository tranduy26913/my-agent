import { apiJson, postJson } from "@/lib/http";
import type { AccountUser, CreatedAccount, UsersApi } from "../types";

/** Bản cài gọi REST thật. `baseUrl` là gốc của nhóm admin, ví dụ "/api/admin" (đi qua BFF của portal). */
export function createHttpUsersApi({ baseUrl }: { baseUrl: string }): UsersApi {
  const base = `${baseUrl.replace(/\/$/, "")}/users`;
  const id = (zitadelId: string) => encodeURIComponent(zitadelId);
  return {
    async list() {
      return (await apiJson<{ items: AccountUser[] }>(base)).items;
    },
    create(email) {
      return postJson<CreatedAccount>(base, { email });
    },
    deactivate(zitadelId) {
      return postJson<AccountUser>(`${base}/${id(zitadelId)}/deactivate`);
    },
    reactivate(zitadelId) {
      return postJson<AccountUser>(`${base}/${id(zitadelId)}/reactivate`);
    },
    async resetPassword(zitadelId) {
      return (await postJson<{ tempPassword: string }>(`${base}/${id(zitadelId)}/password`)).tempPassword;
    },
  };
}
