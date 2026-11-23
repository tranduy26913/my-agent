import Link from "next/link";
import { ArrowUpRight, MessageSquare } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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
      <Card className="py-6">
        <CardContent className="flex flex-col gap-4 px-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-xl font-semibold">Xin chào, {firstName(me.name)}</h2>
            <p className="mt-1 text-sm text-muted-foreground">Chọn một công cụ bên dưới, hoặc hỏi Trợ lý ngay.</p>
          </div>
          <Button asChild size="lg" className="h-10 shrink-0 px-4">
            <a href={CHAT_URL}>
              <MessageSquare />
              Hỏi Trợ lý
              <ArrowUpRight />
            </a>
          </Button>
        </CardContent>
      </Card>

      {SHORTCUT_GROUPS.map((group) => {
        const items = NAV.filter((n) => n.group === group && hasAnyRole(me, n.roles));
        if (items.length === 0) return null;
        return (
          <section key={group} aria-labelledby={`group-${group}`}>
            <h3 id={`group-${group}`} className="mb-3 text-sm font-medium text-muted-foreground">
              {GROUP_LABEL[group]}
            </h3>
            <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {items.map((item) => (
                <li key={item.href}>
                  <Link href={item.href} className="block h-full rounded-xl outline-none focus-visible:ring-3 focus-visible:ring-ring/50">
                    <Card className="h-full transition-colors hover:bg-muted/50">
                      <CardContent className="flex items-start gap-3">
                        <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
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
