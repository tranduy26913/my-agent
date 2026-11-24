import { useEffect, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { FileText, Lock, RotateCcw, TriangleAlert } from "lucide-react";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import type { LibraryApi, LibraryQuery, LibraryStatus } from "../types";

const ALL = "all";
const EMPTY_QUERY: LibraryQuery = { type: "", department: "", status: "hieu-luc", q: "" };

const STATUS_META: Record<LibraryStatus, { label: string; short: string; cls: string }> = {
  "hieu-luc": { label: "Đang hiệu lực", short: "Hiệu lực", cls: "bg-success/10 text-success" },
  "chua-hieu-luc": { label: "Chưa hiệu lực", short: "Sắp có hiệu lực", cls: "bg-warning/10 text-warning" },
  "het-hieu-luc": { label: "Hết hiệu lực", short: "Hết hiệu lực", cls: "bg-muted text-muted-foreground" },
};

/** Nhãn loại văn bản. Mã lạ vẫn hiện nguyên văn, không giấu. */
const DOC_TYPE_LABEL: Record<string, string> = {
  "quy-che": "Quy chế",
  "quy-dinh": "Quy định",
  "quy-trinh": "Quy trình",
  "noi-quy": "Nội quy",
  "chinh-sach": "Chính sách",
  "huong-dan": "Hướng dẫn",
  "thong-bao": "Thông báo",
  "bien-ban-hop": "Biên bản họp",
  "ho-so-du-an": "Hồ sơ dự án",
  "hoi-dap": "Hỏi đáp",
  "chung-tu": "Chứng từ",
};
const typeLabel = (t: string | null) => (t ? (DOC_TYPE_LABEL[t] ?? t) : "—");

/** YYYY-MM-DD -> DD/MM/YYYY */
const fmtDate = (d: string | null) => (d ? d.split("-").reverse().join("/") : null);

function validity(from: string | null, to: string | null): string {
  if (from && to) return `${fmtDate(from)} – ${fmtDate(to)}`;
  if (from) return `Từ ${fmtDate(from)}`;
  if (to) return `Đến ${fmtDate(to)}`;
  return "Không ghi ngày";
}

/** Giữ giá trị qua `ms` rồi mới đổi: ô tìm kiếm không gọi API ở từng phím gõ. */
function useDebounced<T>(value: T, ms: number): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

/**
 * Trang Văn bản: duyệt các văn bản mình được xem, lọc theo loại, phòng ban, hiệu lực. Mặc định chỉ hiện văn bản
 * đang có hiệu lực (thứ người ta thường cần); chọn "Tất cả" để thấy cả bản đã hết hạn.
 */
export function LibraryPage({ api }: { api: LibraryApi }) {
  const [query, setQuery] = useState<LibraryQuery>(EMPTY_QUERY);
  const debouncedQ = useDebounced(query.q, 250);
  const effective = { ...query, q: debouncedQ };

  const { data, isLoading, isPlaceholderData, error, refetch } = useQuery({
    queryKey: ["library", effective],
    queryFn: () => api.list(effective),
    placeholderData: keepPreviousData, // đổi bộ lọc: giữ danh sách cũ trong lúc tải, ô lọc không bị trống
  });
  const loading = isLoading || isPlaceholderData;
  const set = (patch: Partial<LibraryQuery>) => setQuery((q) => ({ ...q, ...patch }));
  const dirty = query.type !== "" || query.department !== "" || query.q !== "" || query.status !== EMPTY_QUERY.status;

  // Chưa có dữ liệu thì không hiện số (tránh nháy "(0)" rồi mới nhảy sang số thật)
  const withCount = (label: string, n: number | undefined) => (n === undefined ? label : `${label} (${n})`);
  const statusCount = (s: LibraryStatus) => (data ? (data.statuses.find((f) => f.value === s)?.count ?? 0) : undefined);

  return (
    <div className="flex flex-col gap-4 text-foreground">
      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
        <Input
          value={query.q}
          onChange={(e) => set({ q: e.target.value })}
          placeholder="Tìm theo tên, số hiệu hoặc mã văn bản"
          aria-label="Tìm văn bản"
          className="bg-card sm:w-72"
        />
        <Select value={query.type || ALL} onValueChange={(v) => set({ type: v === ALL ? "" : v })}>
          <SelectTrigger className="w-full bg-card sm:w-48" aria-label="Loại văn bản">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Mọi loại</SelectItem>
            {data?.docTypes.map((f) => (
              <SelectItem key={f.value} value={f.value}>
                {typeLabel(f.value)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={query.department || ALL} onValueChange={(v) => set({ department: v === ALL ? "" : v })}>
          <SelectTrigger className="w-full bg-card sm:w-44" aria-label="Phòng ban">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Mọi phòng ban</SelectItem>
            {data?.departments.map((f) => (
              <SelectItem key={f.value} value={f.value}>
                {f.value}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {dirty ? (
          <Button type="button" variant="ghost" onClick={() => setQuery(EMPTY_QUERY)}>
            <RotateCcw />
            Đặt lại
          </Button>
        ) : null}
      </div>

      <ToggleGroup
        type="single"
        value={query.status || ALL}
        onValueChange={(v) => v && set({ status: v === ALL ? "" : (v as LibraryStatus) })}
        variant="outline"
        className="flex-wrap justify-start"
        aria-label="Hiệu lực"
      >
        <ToggleGroupItem value="hieu-luc">{withCount("Đang hiệu lực", statusCount("hieu-luc"))}</ToggleGroupItem>
        <ToggleGroupItem value="chua-hieu-luc">{withCount("Chưa hiệu lực", statusCount("chua-hieu-luc"))}</ToggleGroupItem>
        <ToggleGroupItem value="het-hieu-luc">{withCount("Hết hiệu lực", statusCount("het-hieu-luc"))}</ToggleGroupItem>
        <ToggleGroupItem value={ALL}>{withCount("Tất cả", data?.totalVisible)}</ToggleGroupItem>
      </ToggleGroup>

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
              <TableHead className="pl-4">Văn bản</TableHead>
              <TableHead className="hidden w-32 md:table-cell">Loại</TableHead>
              <TableHead className="hidden w-28 sm:table-cell">Phòng ban</TableHead>
              <TableHead className="w-44 pr-4">Hiệu lực</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading && !data
              ? Array.from({ length: 6 }, (_, i) => (
                  <TableRow key={i} className="hover:bg-transparent">
                    <TableCell className="pl-4" colSpan={4}>
                      <Skeleton className="h-5 w-full" />
                    </TableCell>
                  </TableRow>
                ))
              : data?.items.map((d) => {
                  const st = STATUS_META[d.status];
                  return (
                    <TableRow key={d.docId} className={loading ? "opacity-60" : undefined}>
                      <TableCell className="min-w-56 whitespace-normal pl-4">
                        <p className="text-sm font-medium">{d.title}</p>
                        <p className="text-xs text-muted-foreground">
                          {[d.soHieu, d.docId !== d.soHieu ? d.docId : null, d.version ? `phiên bản ${d.version}` : null]
                            .filter(Boolean)
                            .join(" · ")}
                        </p>
                        <p className="text-xs text-muted-foreground md:hidden">
                          {typeLabel(d.docType)} <span className="sm:hidden">· {d.department}</span>
                        </p>
                        {d.classified ? (
                          <p className="mt-1 flex items-start gap-1 text-xs text-warning">
                            <Lock className="mt-0.5 size-3 shrink-0" />
                            Văn bản Mật: Trợ lý không đọc nội dung. Xem bản gốc theo quy định an toàn thông tin.
                          </p>
                        ) : null}
                        {d.supersededBy ? <p className="text-xs text-muted-foreground">Được thay bởi {d.supersededBy}</p> : null}
                        {d.supersedes ? <p className="text-xs text-muted-foreground">Thay cho {d.supersedes}</p> : null}
                      </TableCell>
                      <TableCell className="hidden md:table-cell">{typeLabel(d.docType)}</TableCell>
                      <TableCell className="hidden sm:table-cell">{d.department}</TableCell>
                      <TableCell className="whitespace-normal pr-4">
                        <Badge variant="secondary" className={st.cls}>
                          {st.label}
                        </Badge>
                        <p className="mt-1 text-xs tabular-nums text-muted-foreground">{validity(d.effectiveFrom, d.effectiveTo)}</p>
                      </TableCell>
                    </TableRow>
                  );
                })}
          </TableBody>
        </Table>

        {!loading && !error && data && data.items.length === 0 ? (
          <Empty className="border-0 py-10">
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <FileText />
              </EmptyMedia>
              <EmptyTitle className="text-base">
                {data.totalVisible === 0 ? "Chưa có văn bản nào dành cho bạn" : "Không có văn bản nào khớp bộ lọc"}
              </EmptyTitle>
              <EmptyDescription>
                {data.totalVisible === 0
                  ? "Văn bản chỉ hiện khi bạn thuộc phạm vi được xem."
                  : "Thử chọn \"Tất cả\" ở mục hiệu lực, hoặc bỏ bớt điều kiện lọc."}
              </EmptyDescription>
            </EmptyHeader>
          </Empty>
        ) : null}
      </Card>

      <p className="text-xs text-muted-foreground">
        Chỉ hiện văn bản bạn được phép xem; có những văn bản dành riêng cho phòng ban hoặc vai trò khác thì không hiện ở đây.
        {data ? ` Hiệu lực tính theo ngày ${fmtDate(data.today)}.` : ""}
      </p>
    </div>
  );
}
