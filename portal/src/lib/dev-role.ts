"use server";

import { cookies } from "next/headers";
import { DEV_ROLE_COOKIE } from "./me.server";

/** Đổi vai trò giả để thử menu. Production: không làm gì (getMe() cũng bỏ qua cookie này). */
export async function setDevRole(role: "admin" | "employee"): Promise<void> {
  if (process.env.NODE_ENV === "production") return;
  (await cookies()).set(DEV_ROLE_COOKIE, role, { path: "/", maxAge: 60 * 60 * 24 * 365, sameSite: "lax" });
}
