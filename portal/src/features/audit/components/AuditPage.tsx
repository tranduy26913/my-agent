import { useMemo, useState } from "react";
import { keepPreviousData, useInfiniteQuery } from "@tanstack/react-query";
import { RotateCcw, ScrollText, TriangleAlert } from "lucide-react";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardFooter } from "@/components/ui/card";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";
import type { AuditApi, AuditItem, AuditQuery, Highlight } from "../types";

const ALL = "all";
const EMPTY_QUERY: AuditQuery = { event: "", actor: "", since: "", until: "" };

const HIGHLIGHT_ROW: Record<Exclude<Highlight, null>, string> = {
  alert: "bg-destructive/5 hover:bg-destructive/10",
  warn: "bg-warning/5 hover:bg-warning/10",
};
const HIGHLIGHT_BADGE: Record<Exclude<Highlight, null>, string> = {
  alert: "bg-destructive/10 text-destructive",
  warn: "bg-warning/10 text-warning",
};

/** "14/11 09:42"; khác năm hiện tại thì kèm năm. */
function fmtDateTime(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  const year = d.getFullYear() === new Date().getFullYear() ? "" : `/${d.getFullYear()}`;
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}${year} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** Các trường còn lại của detail dưới dạng "chunks 9 · bytes 1204" (bỏ trường đã có trong phần tóm tắt). */
function detailText(item: AuditItem): string {
  return Object.entries(item.detail)
    .filter(([, v]) => v !== null && v !== "" && typeof v !== "object" && String(v) !== item.summary)
    .map(([k, v]) => `${k.replaceAll("_", " ")} ${typeof v === "boolean" ? (v ? "có" : "không") : v}`)
    .join(" · ");
}

/** Nội dung trang Nhật ký: bộ lọc + bảng + "Tải thêm". Không gồm khung portal (src/shell). */
export function AuditPage({ api }: { api: AuditApi }) {
  const [query, setQuery] = useState<AuditQuery>(EMPTY_QUERY);
  const filtered = Object.values(query).some(Boolean);

  const { data, isLoading, isPlaceholderData, error, refetch, fetchNextPage, hasNextPage, isFetchingNextPage } = useInfiniteQuery({
    queryKey: ["audit", query],
    queryFn: ({ pageParam }) => api.list(query, pageParam),
    initialPageParam: null as number | null,
    getNextPageParam: (last) => last.nextCursor,
    // Đổi bộ lọc: giữ dữ liệu cũ làm "chỗ giữ" để danh sách sự kiện trong ô chọn không bị trống trong lúc tải.
    placeholderData: keepPreviousData,
  });
  const loading = isLoading || isPlaceholderData;

  const items = useMemo(() => data?.pages.flatMap((p) => p.items) ?? [], [data]);
  const facets = data?.pages[0];
  const eventOptions = useMemo(
    () =>
      Object.entries(facets?.eventLabels ?? {})
        .map(([value, label]) => ({ value, label, count: facets?.eventCounts[value] ?? 0 }))
        .sort((a, b) => a.label.localeCompare(b.label, "vi")),
    [facets],
  );

  const set = (patch: Partial<AuditQuery>) => setQuery((q) => ({ ...q, ...patch }));

  return (
    <div className="flex flex-col gap-4 text-foreground">
      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
        <Select value={query.event || ALL} onValueChange={(v) => set({ event: v === ALL ? "" : v })}>
          <SelectTrigger className="w-full bg-card sm:w-56" aria-label="Loại sự kiện">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Mọi sự kiện</SelectItem>
            {eventOptions.map((o) => (
              <SelectItem key={o.value} value={o.value}>
                {o.label} ({o.count})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Input
          value={query.actor}
          onChange={(e) => set({ actor: e.target.value })}
          placeholder="Người thực hiện (email hoặc tên)"
          aria-label="Người thực hiện"
          className="bg-card sm:w-64"
        />
        <div className="flex items-center gap-2">
          <Input type="date" value={query.since} max={query.until || undefined} onChange={(e) => set({ since: e.target.value })} aria-label="Từ ngày" className="bg-card sm:w-40" />
          <span className="text-sm text-muted-foreground">đến</span>
          <Input type="date" value={query.until} min={query.since || undefined} onChange={(e) => set({ until: e.target.value })} aria-label="Đến ngày" className="bg-card sm:w-40" />
        </div>
        {filtered ? (
          <Button type="button" variant="ghost" onClick={() => setQuery(EMPTY_QUERY)}>
            <RotateCcw />
            Bỏ lọc
          </Button>
        ) : null}
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

      <Card className="gap-0 overflow-hidden py-0">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-32 pl-4">Thời gian</TableHead>
              <TableHead className="sm:w-56">Sự kiện</TableHead>
              <TableHead className="hidden w-64 sm:table-cell">Người thực hiện</TableHead>
              <TableHead>Nội dung</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading
              ? Array.from({ length: 6 }, (_, i) => (
                  <TableRow key={i} className="hover:bg-transparent">
                    <TableCell className="pl-4" colSpan={4}>
                      <Skeleton className="h-5 w-full" />
                    </TableCell>
                  </TableRow>
                ))
              : items.map((item) => (
                  <TableRow key={item.id} className={cn(item.highlight && HIGHLIGHT_ROW[item.highlight])}>
                    <TableCell className="pl-4 align-top tabular-nums text-muted-foreground sm:align-middle">{fmtDateTime(item.ts)}</TableCell>
                    <TableCell className="min-w-32 whitespace-normal">
                      <Badge variant="secondary" className={cn("h-auto whitespace-normal rounded-lg text-left", item.highlight && HIGHLIGHT_BADGE[item.highlight])}>
                        {item.label}
                      </Badge>
                    </TableCell>
                    <TableCell className="hidden max-w-64 truncate sm:table-cell">{item.actor}</TableCell>
                    <TableCell className="whitespace-normal">
                      <p className="text-sm">{item.summary || "—"}</p>
                      {/* Điện thoại không đủ chỗ cho cột riêng: đưa người thực hiện xuống dưới nội dung */}
                      <p className="truncate text-xs text-muted-foreground sm:hidden">{item.actor}</p>
                      {detailText(item) ? <p className="text-xs text-muted-foreground">{detailText(item)}</p> : null}
                    </TableCell>
                  </TableRow>
                ))}
          </TableBody>
        </Table>

        {!loading && !error && items.length === 0 ? (
          <Empty className="border-0 py-10">
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <ScrollText />
              </EmptyMedia>
              <EmptyTitle className="text-base">{filtered ? "Không có dòng nào khớp bộ lọc" : "Chưa có sự kiện nào"}</EmptyTitle>
              <EmptyDescription>
                {filtered ? "Thử bỏ bớt điều kiện lọc hoặc mở rộng khoảng ngày." : "Nhật ký sẽ hiện ở đây khi có người dùng hệ thống."}
              </EmptyDescription>
            </EmptyHeader>
          </Empty>
        ) : null}

        {hasNextPage && !loading ? (
          <CardFooter className="justify-center border-t py-3">
            <Button type="button" variant="secondary" disabled={isFetchingNextPage} onClick={() => fetchNextPage()}>
              {isFetchingNextPage ? <Spinner /> : null}
              Tải thêm
            </Button>
          </CardFooter>
        ) : null}
      </Card>

      <p className="text-xs text-muted-foreground">
        Nhật ký chỉ ghi ai làm gì, lúc nào. Nội dung câu hỏi của nhân viên và dữ liệu công cụ trả về không hiện ở đây.
      </p>
    </div>
  );
}
