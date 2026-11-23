import Link from "next/link";
import { ArrowUpRight, MessageSquare } from "lucide-react";
import { getMe } from "@/lib/me.server";
import { hasAnyRole } from "@/lib/me";
import { CHAT_URL, GROUP_LABEL, NAV, type NavGroup } from "@/shell/nav";

const SHORTCUT_GROUPS: NavGroup[] = ["tools", "admin"];

/** Tên gọi thân mật: từ cuối của họ tên ("Lê Thị Bình" -> "Bình"). */
function firstName(full: string) {
  return full.trim().split(/\s+/).pop() ?? full;
}

export default async function HomePage() {
  const me = await getMe();

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-8">
      <section className="flex flex-col gap-4 rounded-2xl bg-p-surface p-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold">Xin chào, {firstName(me.name)}</h2>
          <p className="mt-1 text-sm text-p-muted">Chọn một công cụ bên dưới, hoặc hỏi Trợ lý ngay.</p>
        </div>
        <a
          href={CHAT_URL}
          className="inline-flex h-10 shrink-0 items-center justify-center gap-2 rounded-xl bg-p-primary px-4 text-sm font-medium text-p-on-primary transition-colors hover:bg-p-primary-hover"
        >
          <MessageSquare className="size-4" />
          Hỏi Trợ lý
          <ArrowUpRight className="size-4" />
        </a>
      </section>

      {SHORTCUT_GROUPS.map((group) => {
        const items = NAV.filter((n) => n.group === group && hasAnyRole(me, n.roles));
        if (items.length === 0) return null;
        return (
          <section key={group} aria-labelledby={`group-${group}`}>
            <h3 id={`group-${group}`} className="mb-3 text-sm font-medium text-p-muted">
              {GROUP_LABEL[group]}
            </h3>
            <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {items.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className="flex h-full items-start gap-3 rounded-2xl bg-p-surface p-4 transition-colors hover:bg-p-row-hover"
                  >
                    <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-p-primary-soft text-p-primary">
                      <item.icon className="size-5" />
                    </span>
                    <span className="min-w-0">
                      <span className="flex items-center gap-2 text-sm font-medium">
                        {item.label}
                        {!item.ready && (
                          <span className="rounded-full bg-p-neutral-bg px-2 py-0.5 text-xs font-normal text-p-neutral">
                            Sắp có
                          </span>
                        )}
                      </span>
                      <span className="mt-0.5 block text-sm text-p-muted">{item.description}</span>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}
