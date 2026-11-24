"use server";

import { redirect } from "next/navigation";
import { auth, endSessionUrl, signIn, signOut } from "@/auth";

/** Gốc URL công khai của portal, dùng cho `post_logout_redirect_uri` (phải khớp danh sách đã khai ở Zitadel). */
function portalOrigin(): string {
  return process.env.AUTH_URL?.replace(/\/$/, "") ?? "http://localhost:3100";
}

export async function loginAction(formData: FormData): Promise<void> {
  const to = String(formData.get("callbackUrl") ?? "/");
  // Chỉ nhận đường dẫn nội bộ: chặn open redirect (//evil.com, https://evil.com).
  const safe = to.startsWith("/") && !to.startsWith("//") ? to : "/";
  await signIn("zitadel", { redirectTo: safe });
}

/** Xoá phiên của portal rồi báo Zitadel kết thúc phiên đăng nhập (đăng xuất luôn cả bên chat). */
export async function logoutAction(): Promise<void> {
  const session = await auth();
  await signOut({ redirect: false });
  redirect(endSessionUrl(session?.idToken, `${portalOrigin()}/login`));
}
