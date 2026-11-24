"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "./SidebarNav";
import { ThemeToggle } from "./ThemeToggle";
import { UserMenu } from "./UserMenu";
import { EXTRA_TITLES, findNavItem } from "./nav";

/**
 * Khung dashboard: sidebar bên trái (thu về cột icon hoặc mở rộng; trên điện thoại là drawer), phần còn lại là
 * header + vùng nội dung chiếm hết bề ngang và chiều cao còn lại. Tiêu đề lấy từ nav.ts theo đường dẫn.
 */
export function AppShell({ children, title }: { children: ReactNode; title?: string }) {
  const pathname = usePathname();
  const item = findNavItem(pathname);
  const heading = title ?? item?.label ?? EXTRA_TITLES[pathname] ?? "Portal";

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset className="h-svh min-w-0 overflow-hidden bg-background">
        <header className="z-20 flex h-14 shrink-0 items-center gap-2 border-b bg-card/80 px-3 backdrop-blur sm:px-5">
          <SidebarTrigger className="size-9 text-muted-foreground hover:text-foreground" aria-label="Thu gọn hoặc mở rộng menu" />
          <div className="mx-1 h-5 w-px bg-border" />
          <h1 className="min-w-0 flex-1 truncate text-base font-semibold">{heading}</h1>
          <ThemeToggle />
          <UserMenu />
        </header>
        <main className="min-h-0 w-full flex-1 overflow-y-auto p-4 sm:p-6">{children}</main>
      </SidebarInset>
    </SidebarProvider>
  );
}
