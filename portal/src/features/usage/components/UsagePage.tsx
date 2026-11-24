import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { TriangleAlert } from "lucide-react";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import type { UsageApi, UsageGroup, UsageReport } from "../types";

type View = "byUser" | "byModel" | "byPurpose" | "byDay";

const VIEWS: { id: View; label: string; firstColumn: string }[] = [
  { id: "byUser", label: "Theo người", firstColumn: "Người dùng" },
  { id: "byModel", label: "Theo mô hình", firstColumn: "Mô hình" },
  { id: "byPurpose", label: "Theo mục đích", firstColumn: "Mục đích" },
  { id: "byDay", label: "Theo ngày", firstColumn: "Ngày" },
];

const num = (n: number) => n.toLocaleString("vi-VN");
/** Chi phí rất nhỏ nhưng khác 0 vẫn hiện, để không nhầm với "chưa tốn gì". */
const usd = (n: number) => (n > 0 && n < 0.01 ? "<$0,01" : `$${n.toLocaleString("vi-VN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);
/** "2026-11" → "Tháng 11/2026" */
const monthLabel = (m: string) => `Tháng ${m.slice(5)}/${m.slice(0, 4)}`;
/** "2026-11-23" → "23/11" */
const dayLabel = (d: string) => `${d.slice(8)}/${d.slice(5, 7)}`;

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <Card className="gap-1 py-4">
      <CardHeader className="px-5">
        <CardTitle className="text-sm font-normal text-muted-foreground">{label}</CardTitle>
      </CardHeader>
      <CardContent className="px-5">
        <p className="text-2xl font-semibold tabular-nums">{value}</p>
        {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
      </CardContent>
    </Card>
  );
}

function GroupTable({ view, groups, budget }: { view: View; groups: UsageGroup[]; budget: number }) {
  const meta = VIEWS.find((v) => v.id === view)!;
  const maxCost = Math.max(...groups.map((g) => g.costUsd), 0);
  const perPerson = view === "byUser";
  return (
    <Card className="gap-0 overflow-hidden py-0">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="pl-4">{meta.firstColumn}</TableHead>
            <TableHead className="text-right">Lượt gọi</TableHead>
            <TableHead className="text-right">Token vào</TableHead>
            <TableHead className="text-right">Token ra</TableHead>
            <TableHead className="w-56 pr-4 text-right">Chi phí{perPerson ? ` (ngân sách ${usd(budget)})` : ""}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {groups.map((g) => {
            const over = perPerson && budget > 0 && g.costUsd > budget;
            // Theo người: thanh so với ngân sách; nhóm khác: thanh so với dòng lớn nhất.
            const pct = perPerson ? (budget > 0 ? (g.costUsd / budget) * 100 : 0) : maxCost > 0 ? (g.costUsd / maxCost) * 100 : 0;
            return (
              <TableRow key={g.key}>
                <TableCell className="pl-4">
                  <span className="font-medium">{view === "byDay" ? dayLabel(g.name) : g.name}</span>
                  {g.department ? <span className="ml-2 text-xs text-muted-foreground">{g.department}</span> : null}
                </TableCell>
                <TableCell className="text-right tabular-nums">{num(g.calls)}</TableCell>
                <TableCell className="text-right tabular-nums">{num(g.inputTokens)}</TableCell>
                <TableCell className="text-right tabular-nums">{num(g.outputTokens)}</TableCell>
                <TableCell className="pr-4">
                  <div className="flex items-center justify-end gap-3">
                    <Progress value={Math.min(pct, 100)} aria-label="Tỉ lệ chi phí" className={cn("h-1.5 w-20", over && "[&>div]:bg-destructive")} />
                    <span className={cn("w-16 text-right tabular-nums", over && "font-medium text-destructive")}>{usd(g.costUsd)}</span>
                  </div>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </Card>
  );
}

/** Nội dung trang Chi phí: chọn tháng, bốn số tổng, và bảng theo người / mô hình / mục đích / ngày. */
export function UsagePage({ api }: { api: UsageApi }) {
  const [month, setMonth] = useState<string | undefined>(undefined);
  const [view, setView] = useState<View>("byUser");
  const { data, isLoading, error, refetch } = useQuery<UsageReport>({
    queryKey: ["usage", month ?? "current"],
    queryFn: () => api.report(month),
  });

  const months = data ? Array.from(new Set([...data.months, data.month])).sort().reverse() : [];

  return (
    <div className="flex flex-col gap-4 text-foreground">
      <div className="flex items-center gap-3">
        <Select value={data?.month ?? ""} onValueChange={setMonth} disabled={!data}>
          <SelectTrigger className="w-48 bg-card" aria-label="Tháng">
            <SelectValue placeholder="Đang tải…" />
          </SelectTrigger>
          <SelectContent>
            {months.map((m) => (
              <SelectItem key={m} value={m}>
                {monthLabel(m)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground">Tính theo giờ UTC.</p>
      </div>

      {error ? (
        <Alert variant="destructive" className="flex items-center gap-3 border-0 bg-destructive/10 px-4 py-3">
          <TriangleAlert className="size-4 shrink-0" />
          <p className="min-w-0 flex-1 text-sm">{error.message}</p>
          <Button type="button" variant="link" size="sm" onClick={() => refetch()} className="h-auto shrink-0 p-0 text-destructive">
            Thử lại
          </Button>
        </Alert>
      ) : null}

      {isLoading ? (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {Array.from({ length: 4 }, (_, i) => (
            <Skeleton key={i} className="h-24 rounded-2xl" />
          ))}
        </div>
      ) : null}

      {data ? (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat label="Lượt gọi" value={num(data.calls)} />
            <Stat label="Token vào" value={num(data.inputTokens)} />
            <Stat label="Token ra" value={num(data.outputTokens)} />
            <Stat label="Chi phí" value={usd(data.costUsd)} hint="Model chạy cục bộ không tính tiền" />
          </div>

          {data.calls === 0 ? (
            <Card className="py-6">
              <Empty className="border-0">
                <EmptyHeader>
                  <EmptyTitle className="text-base">Chưa có lượt gọi nào trong {monthLabel(data.month).toLowerCase()}</EmptyTitle>
                  <EmptyDescription>Chọn tháng khác ở ô phía trên.</EmptyDescription>
                </EmptyHeader>
              </Empty>
            </Card>
          ) : (
            <>
              <Tabs value={view} onValueChange={(v) => setView(v as View)}>
                <TabsList>
                  {VIEWS.map((v) => (
                    <TabsTrigger key={v.id} value={v.id}>
                      {v.label}
                    </TabsTrigger>
                  ))}
                </TabsList>
              </Tabs>
              <GroupTable view={view} groups={data[view]} budget={data.budgetUsdPerUser} />
            </>
          )}
        </>
      ) : null}
    </div>
  );
}
