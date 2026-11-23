"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { ChevronDown, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { setDevRole } from "@/lib/dev-role";
import { ROLE_ADMIN } from "@/lib/me";
import { useMe } from "./me-context";

const IS_DEV = process.env.NODE_ENV !== "production";

export function UserMenu() {
  const me = useMe();
  const router = useRouter();
  const [, startTransition] = useTransition();
  const isAdmin = me.roles.includes(ROLE_ADMIN);
  const initial = me.name.trim().charAt(0).toUpperCase();

  function switchRole(role: string) {
    startTransition(async () => {
      await setDevRole(role === "admin" ? "admin" : "employee");
      router.refresh();
    });
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="h-10 gap-2 px-2">
          <span className="flex size-7 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
            {initial}
          </span>
          <span className="hidden max-w-40 truncate sm:block">{me.name}</span>
          <ChevronDown className="text-muted-foreground" />
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="w-72">
        <DropdownMenuLabel className="font-normal">
          <p className="truncate text-sm font-medium text-foreground">{me.name}</p>
          <p className="truncate text-xs text-muted-foreground">{me.email}</p>
          <p className="mt-1 text-xs text-muted-foreground">Vai trò: {isAdmin ? "Quản trị viên" : "Nhân viên"}</p>
        </DropdownMenuLabel>

        {IS_DEV && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuLabel className="text-xs font-normal text-muted-foreground">Chế độ dev: xem với vai trò</DropdownMenuLabel>
            <DropdownMenuRadioGroup value={isAdmin ? "admin" : "employee"} onValueChange={switchRole}>
              <DropdownMenuRadioItem value="admin">Admin</DropdownMenuRadioItem>
              <DropdownMenuRadioItem value="employee">Nhân viên</DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
          </>
        )}

        <DropdownMenuSeparator />
        <DropdownMenuItem disabled title="Chưa có đăng nhập thật. Sẽ nối với Zitadel (docs/06, giai đoạn 5).">
          <LogOut />
          Đăng xuất
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
