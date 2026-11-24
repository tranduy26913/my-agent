import type { ReactNode } from "react";
import { getMe } from "@/lib/me.server";
import { AppShell } from "@/shell/AppShell";
import { MeProvider } from "@/shell/me-context";

/** Khung chung của mọi trang cần đăng nhập. `getMe()` chuyển về /login (hoặc /no-access) nếu không đủ điều kiện. */
export default async function PortalLayout({ children }: { children: ReactNode }) {
  const me = await getMe();
  return (
    <MeProvider me={me}>
      <AppShell>{children}</AppShell>
    </MeProvider>
  );
}
