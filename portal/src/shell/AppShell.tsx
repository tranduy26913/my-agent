"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { Separator } from "@/components/ui/separator";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "./SidebarNav";
import { UserMenu } from "./UserMenu";
import { EXTRA_TITLES, findNavItem } from "./nav";

/**
 * Khung của portal, dựng trên Sidebar của shadcn: cột cố định (máy tính, thu gọn được) hoặc drawer (điện thoại)
 * + header có tên trang và menu người dùng. Tiêu đề lấy từ nav.ts theo đường dẫn.
 */
export function AppShell({ children, title }: { children: ReactNode; title?: string }) {
  const pathname = usePathname();
  const heading = title ?? findNavItem(pathname)?.label ?? EXTRA_TITLES[pathname] ?? "Portal";

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset className="min-w-0">
        <header className="sticky top-0 z-20 flex h-16 items-center gap-2 border-b bg-card px-3 sm:px-6">
          <SidebarTrigger className="-ml-1 size-9" aria-label="Mở hoặc thu gọn menu" />
          <Separator orientation="vertical" className="mr-1 h-5" />
          <h1 className="min-w-0 flex-1 truncate text-lg font-semibold">{heading}</h1>
          <UserMenu />
        </header>
        <div className="p-4 sm:p-6">{children}</div>
      </SidebarInset>
    </SidebarProvider>
  );
}
