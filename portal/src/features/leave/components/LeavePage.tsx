import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CalendarDays, TriangleAlert } from "lucide-react";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import type { Balance, LeaveApi, LeaveRequest, Scope } from "../types";

const KIND_LABEL: Record<string, string> = {
  "phep-nam": "Phép năm",
  "nghi-om-co-luong": "Nghỉ ốm có lương",
  "nghi-viec-rieng-ket-hon": "Nghỉ kết hôn",
  "nghi-sinh-nhat": "Nghỉ sinh nhật",
};
const STATUS_META: Record<string, { label: string; cls: string }> = {
  "cho-duyet": { label: "Chờ duyệt", cls: "bg-warning/10 text-warning" },
  "da-duyet": { label: "Đã duyệt", cls: "bg-success/10 text-success" },
  "tu-choi": { label: "Từ chối", cls: "bg-destructive/10 text-destructive" },
};
const SCOPE_LABEL: Record<Scope, string> = { team: "cấp dưới trực tiếp", dept: "cả phòng", all: "toàn công ty" };

/** 7.5 -> "7,5" */
const num = (n: number) => n.toLocaleString("vi-VN", { maximumFractionDigits: 2 });
/** YYYY-MM-DD -> DD/MM/YYYY */
const fmtDate = (d: string) => d.split("-").reverse().join("/");
const period = (r: LeaveRequest) => (r.fromDate === r.toDate ? fmtDate(r.fromDate) : `${fmtDate(r.fromDate)} – ${fmtDate(r.toDate)}`);
const errText = (e: unknown) => (e instanceof Error ? e.message : "Đã có lỗi xảy ra");

function ErrorBar({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  return (
    <Alert variant="destructive" className="flex items-center gap-3 border-0 bg-destructive/10 px-4 py-3">
      <TriangleAlert className="size-4 shrink-0" />
      <p className="min-w-0 flex-1 text-sm">{errText(error)}</p>
      <Button type="button" variant="link" size="sm" onClick={onRetry} className="h-auto shrink-0 p-0 text-destructive">
        Thử lại
      </Button>
    </Alert>
  );
}

function BalanceCard({ balance, year }: { balance: Balance | null; year: number }) {
  if (!balance) {
    return (
      <Card>
        <Empty className="border-0 py-8">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <CalendarDays />
            </EmptyMedia>
            <EmptyTitle className="text-base">Chưa có số liệu phép năm {year}</EmptyTitle>
            <EmptyDescription>Số dư được đồng bộ từ hệ thống nhân sự. Hãy hỏi bộ phận Nhân sự nếu bạn nghĩ đây là thiếu sót.</EmptyDescription>
          </EmptyHeader>
        </Empty>
      </Card>
    );
  }
  const total = balance.entitled + balance.carriedOver;
  const percentUsed = total > 0 ? Math.min(100, Math.round((balance.used / total) * 100)) : 0;
  return (
    <Card>
      <CardHeader>
        <CardDescription>Phép còn lại năm {balance.year}</CardDescription>
        <CardTitle className="text-4xl font-semibold tabular-nums">
          {num(balance.remaining)} <span className="text-base font-normal text-muted-foreground">ngày</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4">
        <Progress value={percentUsed} aria-label={`Đã dùng ${percentUsed}% phép`} />
        <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm sm:grid-cols-4">
          {[
            ["Được hưởng", balance.entitled],
            ["Tồn chuyển sang", balance.carriedOver],
            ["Tồn đã huỷ", balance.carriedExpired],
            ["Đã dùng", balance.used],
          ].map(([label, value]) => (
            <div key={label as string}>
              <dt className="text-xs text-muted-foreground">{label}</dt>
              <dd className="font-medium tabular-nums">{num(value as number)} ngày</dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}

function RequestsTable({ requests, showEmployee, emptyText }: { requests: LeaveRequest[]; showEmployee?: boolean; emptyText: string }) {
  return (
    <Card className="gap-0 overflow-hidden py-0">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="pl-4">{showEmployee ? "Nhân viên" : "Loại nghỉ"}</TableHead>
            <TableHead className="w-44">Thời gian</TableHead>
            <TableHead className="hidden w-32 sm:table-cell">Trạng thái</TableHead>
            <TableHead className="hidden w-40 pr-4 md:table-cell">Người duyệt</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {requests.map((r) => {
            const st = STATUS_META[r.status] ?? { label: r.status, cls: "bg-muted text-muted-foreground" };
            return (
              <TableRow key={r.code}>
                <TableCell className="min-w-44 whitespace-normal pl-4">
                  <p className="text-sm font-medium">{showEmployee ? r.employee.name : (KIND_LABEL[r.kind] ?? r.kind)}</p>
                  <p className="text-xs text-muted-foreground">
                    {showEmployee ? `${r.employee.department} · ${KIND_LABEL[r.kind] ?? r.kind} · ` : ""}
                    {r.code}
                  </p>
                  {r.note ? <p className="mt-0.5 text-xs text-muted-foreground">{r.note}</p> : null}
                  <Badge variant="secondary" className={`mt-1 sm:hidden ${st.cls}`}>
                    {st.label}
                  </Badge>
                </TableCell>
                <TableCell className="whitespace-normal tabular-nums">
                  <p className="text-sm">{period(r)}</p>
                  <p className="text-xs text-muted-foreground">{num(r.days)} ngày</p>
                </TableCell>
                <TableCell className="hidden sm:table-cell">
                  <Badge variant="secondary" className={st.cls}>
                    {st.label}
                  </Badge>
                </TableCell>
                <TableCell className="hidden pr-4 md:table-cell">{r.approverName ?? "—"}</TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
      {requests.length === 0 ? (
        <Empty className="border-0 py-8">
          <EmptyHeader>
            <EmptyTitle className="text-base">{emptyText}</EmptyTitle>
          </EmptyHeader>
        </Empty>
      ) : null}
    </Card>
  );
}

function TableSkeleton() {
  return (
    <Card className="gap-3 p-4">
      {Array.from({ length: 4 }, (_, i) => (
        <Skeleton key={i} className="h-5 w-full" />
      ))}
    </Card>
  );
}

function TeamPanel({ api, enabled }: { api: LeaveApi; enabled: boolean }) {
  // Mỗi lần gọi backend ghi Nhật ký "xem dữ liệu người khác": chỉ gọi khi tab được mở, không tự làm mới.
  const team = useQuery({ queryKey: ["leave", "team"], queryFn: () => api.team(), enabled, staleTime: 60_000 });
  // null = chưa chọn: mặc định xem đơn chờ duyệt, nhưng nếu không có đơn nào chờ thì xem tất cả cho khỏi thấy bảng trống
  const [picked, setPicked] = useState<"pending" | "all" | null>(null);

  if (team.isLoading) return <TableSkeleton />;
  if (team.error) return <ErrorBar error={team.error} onRetry={() => team.refetch()} />;
  const d = team.data;
  if (!d) return null;

  const pendingCount = d.requests.filter((r) => r.status === "cho-duyet").length;
  const filter = picked ?? (pendingCount > 0 ? "pending" : "all");
  const requests = filter === "pending" ? d.requests.filter((r) => r.status === "cho-duyet") : d.requests;

  return (
    <div className="grid gap-4">
      <p className="text-sm text-muted-foreground">
        Bạn đang xem phép của <span className="font-medium text-foreground">{d.scopes.map((s) => SCOPE_LABEL[s]).join(", ")}</span>. Mỗi lần mở tab này được ghi vào Nhật ký.
      </p>

      <Card className="gap-0 overflow-hidden py-0">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="pl-4">Nhân viên</TableHead>
              <TableHead className="w-28 text-right">Còn lại</TableHead>
              <TableHead className="hidden w-28 text-right sm:table-cell">Đã dùng</TableHead>
              <TableHead className="w-28 pr-4 text-right">Chờ duyệt</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {d.members.map((m) => (
              <TableRow key={m.person.code}>
                <TableCell className="whitespace-normal pl-4">
                  <p className="text-sm font-medium">{m.person.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {m.person.department} · {m.person.title}
                  </p>
                </TableCell>
                <TableCell className="text-right tabular-nums">{m.balance ? num(m.balance.remaining) : "—"}</TableCell>
                <TableCell className="hidden text-right tabular-nums sm:table-cell">{m.balance ? num(m.balance.used) : "—"}</TableCell>
                <TableCell className="pr-4 text-right">
                  {m.pending > 0 ? (
                    <Badge variant="secondary" className="bg-warning/10 text-warning">
                      {m.pending}
                    </Badge>
                  ) : (
                    <span className="text-muted-foreground">0</span>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {d.members.length === 0 ? (
          <Empty className="border-0 py-8">
            <EmptyHeader>
              <EmptyTitle className="text-base">Chưa có ai trong phạm vi bạn được xem</EmptyTitle>
            </EmptyHeader>
          </Empty>
        ) : null}
      </Card>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-medium">Đơn nghỉ</h2>
        <ToggleGroup type="single" value={filter} onValueChange={(v) => v && setPicked(v as "pending" | "all")} variant="outline" aria-label="Lọc đơn">
          <ToggleGroupItem value="pending">Chờ duyệt ({pendingCount})</ToggleGroupItem>
          <ToggleGroupItem value="all">Tất cả ({d.requests.length})</ToggleGroupItem>
        </ToggleGroup>
      </div>
      <RequestsTable requests={requests} showEmployee emptyText={filter === "pending" ? "Không có đơn nào đang chờ duyệt" : "Chưa có đơn nghỉ nào"} />
    </div>
  );
}

/**
 * Trang Nghỉ phép: số dư và đơn nghỉ của chính mình; quản lý thêm tab "Nhóm của tôi" (phạm vi theo ADR-003).
 * Chỉ xem: gửi và duyệt đơn vẫn làm trên HRM.
 */
export function LeavePage({ api }: { api: LeaveApi }) {
  const me = useQuery({ queryKey: ["leave", "me"], queryFn: () => api.me() });
  const [tab, setTab] = useState("me");

  if (me.isLoading) {
    return (
      <div className="grid gap-4">
        <Skeleton className="h-40 w-full rounded-2xl" />
        <TableSkeleton />
      </div>
    );
  }
  if (me.error) return <ErrorBar error={me.error} onRetry={() => me.refetch()} />;
  const d = me.data;
  if (!d) return null;

  const mine = (
    <div className="grid gap-4">
      <BalanceCard balance={d.balance} year={d.year} />
      <h2 className="text-sm font-medium">Đơn nghỉ của bạn</h2>
      <RequestsTable requests={d.requests} emptyText="Bạn chưa có đơn nghỉ nào" />
    </div>
  );

  return (
    <div className="w-full flex flex-col gap-4 text-foreground">
      {d.canViewTeam ? (
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList aria-label="Chế độ xem">
            <TabsTrigger value="me">Của tôi</TabsTrigger>
            <TabsTrigger value="team">Nhóm của tôi</TabsTrigger>
          </TabsList>
          <TabsContent value="me">{mine}</TabsContent>
          <TabsContent value="team">
            <TeamPanel api={api} enabled={tab === "team"} />
          </TabsContent>
        </Tabs>
      ) : (
        mine
      )}
      <p className="text-xs text-muted-foreground">
        Chỉ để xem. Gửi và duyệt đơn nghỉ vẫn làm trên HRM. Số liệu có thể chậm hơn HRM một chút.
      </p>
    </div>
  );
}
