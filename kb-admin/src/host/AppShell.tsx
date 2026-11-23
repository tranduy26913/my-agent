import type { ReactNode } from "react";
import { ArrowUpRight, Library, MessageSquare } from "lucide-react";

const CHAT_URL = process.env.NEXT_PUBLIC_CHAT_URL ?? "http://localhost:3080";

/**
 * Khung của ứng dụng chủ: sidebar + header. KHÔNG thuộc mô-đun Kho tri thức.
 * Trong LibreChat, khung này là thanh bên và header sẵn có của họ.
 */
export function AppShell({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex min-h-dvh">
      <aside className="sticky top-0 hidden h-dvh w-60 shrink-0 flex-col bg-kb-surface lg:flex">
        <div className="flex h-16 items-center gap-2.5 border-b border-kb-line px-5">
          <span className="flex size-7 items-center justify-center rounded-lg bg-kb-primary text-kb-on-primary">
            <Library className="size-4" />
          </span>
          <span className="text-sm font-semibold">Trợ lý số Sao Việt</span>
        </div>
        <nav aria-label="Điều hướng chính" className="flex flex-1 flex-col gap-1 px-3 py-3">
          <a
            href="/kb"
            aria-current="page"
            className="flex h-10 items-center gap-2.5 rounded-xl bg-kb-primary-soft px-3 text-sm font-medium text-kb-primary"
          >
            <Library className="size-4 shrink-0" />Kho tri thức
          </a>
          <a
            href={CHAT_URL}
            className="mt-auto flex h-10 items-center gap-2.5 rounded-xl px-3 text-sm text-kb-fg/70 transition-colors hover:bg-kb-hover hover:text-kb-fg"
          >
            <MessageSquare className="size-4 shrink-0" />Mở Trợ lý
            <ArrowUpRight className="ml-auto size-4 shrink-0 text-kb-muted" />
          </a>
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-kb-line bg-kb-surface px-4 sm:px-6">
          <span className="flex size-7 items-center justify-center rounded-lg bg-kb-primary text-kb-on-primary lg:hidden">
            <Library className="size-4" />
          </span>
          <h1 className="text-lg font-semibold">{title}</h1>
        </header>
        <main className="p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}
