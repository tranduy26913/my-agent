"use client";

import { useEffect, useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";
import { SidebarNav } from "./SidebarNav";
import { UserMenu } from "./UserMenu";
import { EXTRA_TITLES, findNavItem } from "./nav";

/**
 * Khung của portal: sidebar cố định (máy tính) hoặc drawer (điện thoại) + header có tên trang và menu người dùng.
 * Tiêu đề lấy từ nav.ts theo đường dẫn, trang không có trong nav thì tự đặt `title`.
 */
export function AppShell({ children, title }: { children: ReactNode; title?: string }) {
  const pathname = usePathname();
  const [drawerFor, setDrawerFor] = useState<string | null>(null);
  // Drawer gắn với đường dẫn lúc mở: đổi trang là tự đóng, không cần effect.
  const drawerOpen = drawerFor === pathname;
  const close = () => setDrawerFor(null);

  useEffect(() => {
    if (!drawerOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setDrawerFor(null);
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [drawerOpen]);

  const heading = title ?? findNavItem(pathname)?.label ?? EXTRA_TITLES[pathname] ?? "Portal";

  return (
    <div className="flex min-h-dvh">
      <aside className="sticky top-0 hidden h-dvh w-60 shrink-0 flex-col bg-p-surface lg:flex">
        <SidebarNav />
      </aside>

      {drawerOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button type="button" aria-label="Đóng menu" onClick={close} className="absolute inset-0 bg-black/30" />
          <aside
            role="dialog"
            aria-modal="true"
            aria-label="Menu"
            className="absolute inset-y-0 left-0 flex w-64 max-w-[85vw] flex-col bg-p-surface shadow-p-modal"
          >
            <button
              type="button"
              onClick={close}
              aria-label="Đóng menu"
              className="absolute right-2 top-3 flex size-10 items-center justify-center rounded-xl text-p-muted hover:bg-p-hover"
            >
              <X className="size-5" />
            </button>
            <SidebarNav onNavigate={close} />
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-16 items-center gap-2 border-b border-p-line bg-p-surface px-3 sm:px-6">
          <button
            type="button"
            onClick={() => setDrawerFor(pathname)}
            aria-label="Mở menu"
            aria-expanded={drawerOpen}
            className="flex size-10 items-center justify-center rounded-xl text-p-fg/70 hover:bg-p-hover lg:hidden"
          >
            <Menu className="size-5" />
          </button>
          <h1 className="min-w-0 flex-1 truncate text-lg font-semibold">{heading}</h1>
          <UserMenu />
        </header>
        <main className="p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}
