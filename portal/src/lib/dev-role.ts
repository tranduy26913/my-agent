"use server";

import { cookies } from "next/headers";
import { DEV_AUTH, DEV_ROLE_COOKIE } from "./me.server";

/** Đổi vai trò giả để thử menu. Chỉ có tác dụng khi PORTAL_DEV_AUTH=1 (getMe() cũng bỏ qua cookie này nếu không). */
export async function setDevRole(role: "admin" | "employee"): Promise<void> {
  if (!DEV_AUTH) return;
  (await cookies()).set(DEV_ROLE_COOKIE, role, { path: "/", maxAge: 60 * 60 * 24 * 365, sameSite: "lax" });
}
