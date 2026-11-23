import type { ReactNode } from "react";
import { redirect } from "next/navigation";
import { getMe } from "@/lib/me.server";
import { ROLE_ADMIN, hasAnyRole } from "@/lib/me";

/**
 * Cổng chung của mọi trang /admin/*. Ẩn menu chỉ để gọn (nav.ts); đây mới là chỗ chặn khi gõ thẳng URL.
 * API phía sau vẫn tự kiểm quyền, không dựa vào lớp này.
 */
export default async function AdminLayout({ children }: { children: ReactNode }) {
  const me = await getMe();
  if (!hasAnyRole(me, [ROLE_ADMIN])) redirect("/403?need=admin");
  return children;
}
