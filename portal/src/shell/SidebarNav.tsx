"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ArrowUpRight, Library, MessageSquare } from "lucide-react";
import { hasAnyRole } from "@/lib/me";
import { useMe } from "./me-context";
import { CHAT_URL, GROUP_LABEL, NAV, type NavGroup, type NavItem } from "./nav";

const GROUPS: NavGroup[] = ["main", "tools", "admin"];

function isActive(item: NavItem, pathname: string) {
  return item.href === "/" ? pathname === "/" : pathname === item.href || pathname.startsWith(`${item.href}/`);
}

/** Nội dung sidebar, dùng chung cho cột cố định (máy tính) và drawer (điện thoại). */
export function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const me = useMe();

  return (
    <>
      <div className="flex h-16 shrink-0 items-center gap-2.5 border-b border-p-line px-5">
        <span className="flex size-7 items-center justify-center rounded-lg bg-p-primary text-p-on-primary">
          <Library className="size-4" />
        </span>
        <span className="text-sm font-semibold">Trợ lý số Sao Việt</span>
      </div>

      <nav aria-label="Điều hướng chính" className="flex flex-1 flex-col gap-0.5 overflow-y-auto px-3 py-3">
        {GROUPS.map((group) => {
          const items = NAV.filter((n) => n.group === group && hasAnyRole(me, n.roles));
          if (items.length === 0) return null;
          const label = GROUP_LABEL[group];
          return (
            <div key={group} className={group === "main" ? "" : "mt-4"}>
              {label && <p className="px-3 pb-1.5 text-xs font-medium uppercase tracking-wide text-p-muted">{label}</p>}
              <ul className="flex flex-col gap-0.5">
                {items.map((item) => {
                  const active = isActive(item, pathname);
                  return (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        onClick={onNavigate}
                        aria-current={active ? "page" : undefined}
                        className={
                          "flex h-10 items-center gap-2.5 rounded-xl px-3 text-sm transition-colors " +
                          (active
                            ? "bg-p-primary-soft font-medium text-p-primary"
                            : "text-p-fg/70 hover:bg-p-hover hover:text-p-fg")
                        }
                      >
                        <item.icon className="size-4 shrink-0" />
                        {item.label}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          );
        })}

        <a
          href={CHAT_URL}
          className="mt-auto flex h-10 items-center gap-2.5 rounded-xl px-3 text-sm text-p-fg/70 transition-colors hover:bg-p-hover hover:text-p-fg"
        >
          <MessageSquare className="size-4 shrink-0" />
          Mở Trợ lý
          <ArrowUpRight className="ml-auto size-4 shrink-0 text-p-muted" />
        </a>
      </nav>
    </>
  );
}
