import { useEffect, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { BookUser, Mail, Phone, TriangleAlert } from "lucide-react";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { DirectoryApi, DirectoryEntry } from "../types";

const ALL = "all";

/** Giữ giá trị qua `ms` rồi mới đổi: ô tìm kiếm không gọi API ở từng phím gõ. */
function useDebounced<T>(value: T, ms: number): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

function PhoneCell({ e }: { e: DirectoryEntry }) {
  if (e.phone) {
    return (
      <a href={`tel:${e.phone.replace(/\s/g, "")}`} className="inline-flex items-center gap-1 tabular-nums underline-offset-4 hover:underline">
        <Phone className="size-3 shrink-0 text-muted-foreground" />
        {e.phone}
      </a>
    );
  }
  return (
    <span className="text-xs text-muted-foreground">{e.phoneVisible ? "Chưa có số" : "Chỉ người cùng phòng xem được"}</span>
  );
}

/** Trang Danh bạ: tìm đồng nghiệp theo tên, phòng ban. Số điện thoại hiện theo quyền (backend quyết định, không phải giao diện). */
export function DirectoryPage({ api }: { api: DirectoryApi }) {
  const [q, setQ] = useState("");
  const [department, setDepartment] = useState("");
  const debouncedQ = useDebounced(q, 250);

  const { data, isLoading, isPlaceholderData, error, refetch } = useQuery({
    queryKey: ["directory", debouncedQ, department],
    queryFn: () => api.list({ q: debouncedQ, department }),
    placeholderData: keepPreviousData,
  });
  const loading = isLoading || isPlaceholderData;

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-4 text-foreground">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Tìm theo tên, email hoặc chức danh (gõ không dấu cũng được)"
          aria-label="Tìm đồng nghiệp"
          className="bg-card sm:w-96"
        />
        <Select value={department || ALL} onValueChange={(v) => setDepartment(v === ALL ? "" : v)}>
          <SelectTrigger className="w-full bg-card sm:w-48" aria-label="Phòng ban">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Mọi phòng ban</SelectItem>
            {data?.departments.map((d) => (
              <SelectItem key={d} value={d}>
                {d}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {data ? (
          <p className="text-sm text-muted-foreground sm:ml-auto" aria-live="polite">
            {data.items.length} người
          </p>
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
              <TableHead className="pl-4">Họ tên</TableHead>
              <TableHead className="hidden w-28 sm:table-cell">Phòng ban</TableHead>
              <TableHead className="hidden md:table-cell">Email</TableHead>
              <TableHead className="w-48 pr-4">Điện thoại</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading && !data
              ? Array.from({ length: 8 }, (_, i) => (
                  <TableRow key={i} className="hover:bg-transparent">
                    <TableCell className="pl-4" colSpan={4}>
                      <Skeleton className="h-5 w-full" />
                    </TableCell>
                  </TableRow>
                ))
              : data?.items.map((e) => (
                  <TableRow key={e.person.code} className={loading ? "opacity-60" : undefined}>
                    <TableCell className="min-w-48 whitespace-normal pl-4">
                      <p className="flex flex-wrap items-center gap-x-2 text-sm font-medium">
                        {e.person.name}
                        {!e.active ? (
                          <Badge variant="outline" className="font-normal text-muted-foreground">
                            Đã nghỉ việc
                          </Badge>
                        ) : null}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {e.person.title} <span className="sm:hidden">· {e.person.department}</span>
                      </p>
                      <a href={`mailto:${e.email}`} className="mt-0.5 inline-flex items-center gap-1 break-all text-xs text-muted-foreground underline-offset-4 hover:underline md:hidden">
                        <Mail className="size-3 shrink-0" />
                        {e.email}
                      </a>
                    </TableCell>
                    <TableCell className="hidden sm:table-cell">{e.person.department}</TableCell>
                    <TableCell className="hidden md:table-cell">
                      <a href={`mailto:${e.email}`} className="break-all underline-offset-4 hover:underline">
                        {e.email}
                      </a>
                    </TableCell>
                    <TableCell className="whitespace-normal pr-4">
                      <PhoneCell e={e} />
                    </TableCell>
                  </TableRow>
                ))}
          </TableBody>
        </Table>

        {!loading && !error && data && data.items.length === 0 ? (
          <Empty className="border-0 py-10">
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <BookUser />
              </EmptyMedia>
              <EmptyTitle className="text-base">Không tìm thấy ai</EmptyTitle>
              <EmptyDescription>Thử gõ ít chữ hơn, hoặc chọn “Mọi phòng ban”.</EmptyDescription>
            </EmptyHeader>
          </Empty>
        ) : null}
      </Card>

      {data?.truncated ? (
        <p className="text-sm text-muted-foreground">Còn nhiều người nữa: hãy gõ thêm tên hoặc chọn phòng ban để thu hẹp.</p>
      ) : null}
      <p className="text-xs text-muted-foreground">
        Số điện thoại chỉ hiện với người cùng phòng ban (Nhân sự và Ban điều hành xem được mọi số). Tên, phòng ban, chức danh và email thì ai cũng xem được.
      </p>
    </div>
  );
}
