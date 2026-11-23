"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ArrowUpRight, Library, MessageSquare } from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";
import { hasAnyRole } from "@/lib/me";
import { useMe } from "./me-context";
import { CHAT_URL, GROUP_LABEL, NAV, findNavItem, type NavGroup } from "./nav";

const GROUPS: NavGroup[] = ["main", "tools", "admin"];

/** Mục menu kiểu cũ: cao 40px, chữ mờ, rê chuột nền xám; mục đang mở nền chàm nhạt, chữ chàm, đậm. */
const NAV_BUTTON =
  "h-10 text-sm text-foreground/70 hover:bg-muted hover:text-foreground data-active:bg-primary/8 data-active:font-medium data-active:text-primary data-active:hover:bg-primary/8 data-active:hover:text-primary";

/** Sidebar của portal. Trên điện thoại shadcn tự biến thành drawer (Sheet), có bẫy phím Tab và đóng bằng Esc. */
export function AppSidebar() {
  const pathname = usePathname();
  const me = useMe();
  const { setOpenMobile } = useSidebar();
  const current = findNavItem(pathname);

  return (
    <Sidebar>
      <SidebarHeader className="h-16 flex-row items-center gap-2.5 border-b px-5">
        <span className="flex size-7 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <Library className="size-4" />
        </span>
        <span className="text-sm font-semibold">Trợ lý số Sao Việt</span>
      </SidebarHeader>

      <SidebarContent className="px-1 py-2">
        {GROUPS.map((group) => {
          const items = NAV.filter((n) => n.group === group && hasAnyRole(me, n.roles));
          if (items.length === 0) return null;
          const label = GROUP_LABEL[group];
          return (
            <SidebarGroup key={group}>
              {label && <SidebarGroupLabel className="px-3 uppercase tracking-wide text-muted-foreground">{label}</SidebarGroupLabel>}
              <SidebarGroupContent>
                <SidebarMenu>
                  {items.map((item) => (
                    <SidebarMenuItem key={item.href}>
                      <SidebarMenuButton asChild isActive={current?.href === item.href} className={NAV_BUTTON}>
                        <Link href={item.href} onClick={() => setOpenMobile(false)}>
                          <item.icon />
                          {item.label}
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          );
        })}
      </SidebarContent>

      <SidebarFooter className="p-3">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton asChild className={NAV_BUTTON}>
              <a href={CHAT_URL}>
                <MessageSquare />
                Mở Trợ lý
                <ArrowUpRight className="ml-auto text-muted-foreground" />
              </a>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}
