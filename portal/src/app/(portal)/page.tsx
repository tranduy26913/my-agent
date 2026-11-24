import Link from "next/link";
import { ArrowUpRight, MessageSquare, ShieldCheck, Sparkles, Wrench } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { getMe } from "@/lib/me.server";
import { hasAnyRole, ROLE_ADMIN } from "@/lib/me";
import { CHAT_URL, GROUP_LABEL, NAV, type NavGroup } from "@/shell/nav";

const SHORTCUT_GROUPS: NavGroup[] = ["tools", "admin"];

/** Tên gọi thân mật: từ cuối của họ tên ("Lê Thị Bình" -> "Bình"). */
function firstName(full: string) {
  return full.trim().split(/\s+/).pop() ?? full;
}

export default async function HomePage() {
  const me = await getMe();
  const visible = (group: NavGroup) => NAV.filter((n) => n.group === group && !n.hidden && hasAnyRole(me, n.roles));
  const tools = visible("tools");
  const admin = visible("admin");
  const isAdmin = me.roles.includes(ROLE_ADMIN);

  const stats = [
    { label: "Công cụ dùng được", value: tools.filter((t) => t.ready).length, icon: Wrench },
    { label: "Mục quản trị", value: admin.length, icon: ShieldCheck },
    { label: "Vai trò", value: isAdmin ? "Quản trị viên" : "Nhân viên", icon: Sparkles },
  ];

  return (
    <div className="flex w-full flex-col gap-6">
      {/* Hàng đầu: lời chào + thẻ thống kê */}
      <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <Card className="justify-center bg-gradient-to-br from-primary/25 via-primary/10 to-card py-6 ring-1 ring-primary/20">
          <CardContent className="flex flex-col gap-4 px-6">
            <div>
              <h2 className="text-2xl font-semibold">Xin chào, {firstName(me.name)}</h2>
              <p className="mt-1 text-sm text-muted-foreground">Chọn một công cụ bên dưới, hoặc hỏi Trợ lý ngay.</p>
            </div>
            <Button asChild size="lg" className="h-10 w-fit px-4">
              <a href={CHAT_URL}>
                <MessageSquare />
                Hỏi Trợ lý
                <ArrowUpRight />
              </a>
            </Button>
          </CardContent>
        </Card>

        <ul className="grid gap-4 sm:grid-cols-3">
          {stats.map((s) => (
            <li key={s.label}>
              <Card className="h-full py-5">
                <CardContent className="flex h-full flex-col justify-between gap-4 px-5">
                  <span className="flex size-10 items-center justify-center rounded-xl bg-primary/15 text-primary-ink">
                    <s.icon className="size-5" />
                  </span>
                  <div>
                    <p className="text-2xl font-semibold tabular-nums">{s.value}</p>
                    <p className="text-sm text-muted-foreground">{s.label}</p>
                  </div>
                </CardContent>
              </Card>
            </li>
          ))}
        </ul>
      </div>

      {SHORTCUT_GROUPS.map((group) => {
        const items = group === "tools" ? tools : admin;
        if (items.length === 0) return null;
        return (
          <section key={group} aria-labelledby={`group-${group}`}>
            <h3 id={`group-${group}`} className="mb-3 text-sm font-semibold tracking-wide text-muted-foreground uppercase">
              {GROUP_LABEL[group]}
            </h3>
            <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
              {items.map((item) => (
                <li key={item.href}>
                  <Link href={item.href} className="block h-full rounded-2xl outline-none focus-visible:ring-3 focus-visible:ring-ring/50">
                    <Card className="h-full ring-1 ring-transparent transition hover:-translate-y-0.5 hover:shadow-md hover:ring-primary/40">
                      <CardContent className="flex items-start gap-3">
                        <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/15 text-primary-ink">
                          <item.icon className="size-5" />
                        </span>
                        <span className="min-w-0">
                          <span className="flex items-center gap-2 text-sm font-medium">
                            {item.label}
                            {!item.ready && <Badge variant="secondary">Sắp có</Badge>}
                          </span>
                          <span className="mt-0.5 block text-sm text-muted-foreground">{item.description}</span>
                        </span>
                      </CardContent>
                    </Card>
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
