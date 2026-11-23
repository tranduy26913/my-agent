import type { ReactNode } from "react";
import { getMe } from "@/lib/me.server";
import { AppShell } from "@/shell/AppShell";
import { MeProvider } from "@/shell/me-context";

/** Khung chung của mọi trang cần đăng nhập. Chưa có đăng nhập thật nên `getMe()` đang là bản giả. */
export default async function PortalLayout({ children }: { children: ReactNode }) {
  const me = await getMe();
  return (
    <MeProvider me={me}>
      <AppShell>{children}</AppShell>
    </MeProvider>
  );
}
