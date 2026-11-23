"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronDown, LogOut } from "lucide-react";
import { setDevRole } from "@/lib/dev-role";
import { ROLE_ADMIN } from "@/lib/me";
import { useMe } from "./me-context";

const IS_DEV = process.env.NODE_ENV !== "production";

export function UserMenu() {
  const me = useMe();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const isAdmin = me.roles.includes(ROLE_ADMIN);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  async function switchRole(role: "admin" | "employee") {
    setOpen(false);
    await setDevRole(role);
    router.refresh();
  }

  const initial = me.name.trim().charAt(0).toUpperCase();

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex h-10 items-center gap-2 rounded-xl px-2 text-sm transition-colors hover:bg-p-hover"
      >
        <span className="flex size-7 items-center justify-center rounded-full bg-p-primary-soft text-xs font-semibold text-p-primary">
          {initial}
        </span>
        <span className="hidden max-w-40 truncate sm:block">{me.name}</span>
        <ChevronDown className="size-4 text-p-muted" />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-full z-30 mt-2 w-72 rounded-xl border border-p-line-strong bg-p-surface p-1.5 shadow-p-modal"
        >
          <div className="px-3 py-2">
            <p className="truncate text-sm font-medium">{me.name}</p>
            <p className="truncate text-xs text-p-muted">{me.email}</p>
            <p className="mt-1 text-xs text-p-muted">Vai trò: {isAdmin ? "Quản trị viên" : "Nhân viên"}</p>
          </div>

          {IS_DEV && (
            <div className="border-t border-p-line px-3 py-2">
              <p className="mb-1.5 text-xs text-p-muted">Chế độ dev: xem với vai trò</p>
              <div className="flex gap-1 rounded-lg bg-p-tab-selected p-0.5" role="group" aria-label="Đổi vai trò (chỉ chế độ dev)">
                {(["admin", "employee"] as const).map((r) => {
                  const current = (r === "admin") === isAdmin;
                  return (
                    <button
                      key={r}
                      type="button"
                      onClick={() => switchRole(r)}
                      aria-pressed={current}
                      className={
                        "h-8 flex-1 rounded-md text-xs transition-colors " +
                        (current ? "bg-p-surface font-medium shadow-sm" : "text-p-muted hover:text-p-fg")
                      }
                    >
                      {r === "admin" ? "Admin" : "Nhân viên"}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          <div className="border-t border-p-line pt-1">
            <button
              type="button"
              disabled
              title="Chưa có đăng nhập thật. Sẽ nối với Zitadel (docs/06, giai đoạn 5)."
              className="flex h-10 w-full cursor-not-allowed items-center gap-2.5 rounded-lg px-3 text-sm text-p-muted"
            >
              <LogOut className="size-4" />
              Đăng xuất
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
