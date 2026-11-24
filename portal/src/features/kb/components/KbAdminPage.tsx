import { useMemo, useState } from "react";
import { RefreshCw, Search, Trash2, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardFooter } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useKbHost } from "../host";
import { isBusy, useDocuments, useKbMutations } from "../hooks";
import { fold } from "../format";
import { STATUS_META, STATUS_ORDER } from "../labels";
import type { DocStatus } from "../types";
import { ConfirmDialog } from "./ConfirmDialog";
import { DetailPanel } from "./DetailPanel";
import { DocumentTable } from "./DocumentTable";
import { UploadPanel } from "./UploadPanel";
import { ErrorBanner } from "./ui";

type Filter = "all" | DocStatus;

/**
 * Nội dung trang Kho tri thức: thanh công cụ + bảng + hai panel.
 * KHÔNG gồm sidebar / header: đó là khung của portal (src/shell).
 */
export function KbAdminPage() {
  const { route } = useKbHost();
  const { data, isLoading, error, refetch } = useDocuments();
  const { reindex, remove } = useKbMutations();
  const mutationError = reindex.error ?? remove.error;

  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [confirmBulkDelete, setConfirmBulkDelete] = useState(false);

  const docs = useMemo(() => data ?? [], [data]);
  const counts = useMemo(() => {
    const c: Record<Filter, number> = { all: docs.length, ready: 0, processing: 0, error: 0, quarantined: 0 };
    docs.forEach((d) => { c[d.status] += 1; });
    return c;
  }, [docs]);

  const rows = useMemo(() => {
    const q = fold(query.trim());
    return docs.filter(
      (d) =>
        (filter === "all" || d.status === filter) &&
        (!q || fold(`${d.title} ${d.docId} ${d.soHieu ?? ""}`).includes(q)),
    );
  }, [docs, filter, query]);

  // Chỉ giữ lựa chọn của dòng còn tồn tại (sau khi xoá, lọc đổi)
  const selectedIds = rows.map((r) => r.docId).filter((id) => selected.has(id));
  const hasSelection = selectedIds.length > 0;

  const tabs: { id: Filter; label: string }[] = [
    { id: "all", label: "Tất cả" },
    ...STATUS_ORDER.map((s) => ({ id: s as Filter, label: STATUS_META[s].label })),
  ];

  function toggle(id: string) {
    setSelected((cur) => {
      const next = new Set(cur);
      if (!next.delete(id)) next.add(id);
      return next;
    });
  }
  function toggleAll(checked: boolean) {
    setSelected(checked ? new Set(rows.map((r) => r.docId)) : new Set());
  }

  const emptyText = docs.length === 0 ? "Kho chưa có tài liệu nào. Bấm “Nạp tài liệu” để bắt đầu." : "Không có tài liệu khớp bộ lọc";
  const bulkDocs = docs.filter((d) => selectedIds.includes(d.docId));

  return (
    <div className="flex flex-col gap-4 text-foreground">
      {hasSelection ? (
        <div className="flex h-10 items-center gap-3">
          <p className="text-sm font-medium"><span className="tabular-nums">{selectedIds.length}</span> tài liệu đã chọn</p>
          <Button type="button" variant="link" onClick={() => setSelected(new Set())} className="h-auto p-0 text-muted-foreground hover:text-foreground">Bỏ chọn</Button>
          <div className="ml-auto flex gap-2">
            <Button
              type="button"
              variant="outline"
              size="lg"
              className="h-10 px-3"
              disabled={isBusy(reindex)}
              onClick={() => reindex.mutate(selectedIds, { onSuccess: () => setSelected(new Set()) })}
            >
              <RefreshCw />Nạp lại
            </Button>
            <Button type="button" variant="destructive" size="lg" className="h-10 px-3" onClick={() => setConfirmBulkDelete(true)}>
              <Trash2 />Gỡ khỏi kho
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-3">
          {/* Dưới sm: tab thành ô chọn */}
          <div className="sm:hidden">
            <Select value={filter} onValueChange={(v) => setFilter(v as Filter)}>
              <SelectTrigger aria-label="Lọc theo trạng thái" className="h-10 bg-card">
                <span className="text-muted-foreground">Trạng thái:</span>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {tabs.map((t) => <SelectItem key={t.id} value={t.id}>{t.label} · {counts[t.id]}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          <Tabs value={filter} onValueChange={(v) => setFilter(v as Filter)} className="hidden min-w-0 sm:block">
            <TabsList aria-label="Lọc theo trạng thái" className="max-w-full overflow-x-auto">
              {tabs.map((t) => (
                <TabsTrigger key={t.id} value={t.id}>
                  {t.label} <span className="ml-1 tabular-nums">{counts[t.id]}</span>
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>

          <div className="ml-auto flex w-full items-center gap-2 sm:w-auto">
            <div className="relative flex-1 sm:w-64 sm:flex-none">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                type="search"
                aria-label="Tìm tài liệu"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Tìm theo tên, mã, số hiệu"
                className="h-10 bg-card pl-9"
              />
            </div>
            <Button type="button" size="lg" className="h-10 shrink-0 px-4" onClick={() => route.open("upload")}>
              <Upload />Nạp tài liệu
            </Button>
          </div>
        </div>
      )}

      {error ? <ErrorBanner message={error instanceof Error ? error.message : "Không tải được danh sách tài liệu"} onRetry={() => void refetch()} /> : null}
      {/* Backend thật có thể từ chối hoặc xong một phần; thông báo lỗi lấy từ `detail` của API */}
      {mutationError ? <ErrorBanner message={mutationError instanceof Error ? mutationError.message : "Thao tác không thành công"} /> : null}

      <Card className="@container gap-0 rounded-xl border py-0">
        <DocumentTable
          rows={rows}
          loading={isLoading}
          selected={selected}
          onToggle={toggle}
          onToggleAll={toggleAll}
          onOpen={(id) => route.open("detail", id)}
          emptyText={emptyText}
        />
        {docs.length > 0 ? (
          <CardFooter className="border-t bg-transparent px-4 py-3">
            <p className="text-sm tabular-nums text-muted-foreground">
              {rows.length === docs.length ? `${docs.length} tài liệu` : `${rows.length} trong ${docs.length} tài liệu`} · {docs.reduce((n, d) => n + d.chunkCount, 0)} đoạn đã index
            </p>
          </CardFooter>
        ) : null}
      </Card>

      <UploadPanel open={route.panel === "upload"} onClose={route.close} />
      <DetailPanel open={route.panel === "detail"} docId={route.docId} onClose={route.close} />

      {confirmBulkDelete ? (
        <ConfirmDialog
          title={`Gỡ ${bulkDocs.length} tài liệu khỏi kho?`}
          confirmLabel={`Gỡ ${bulkDocs.length} tài liệu`}
          busy={isBusy(remove)}
          onCancel={() => setConfirmBulkDelete(false)}
          onConfirm={() =>
            remove.mutate(bulkDocs.map((d) => d.docId), {
              // đóng cả khi lỗi: danh sách đã tải lại, thông báo lỗi nằm ở banner phía trên
              onSettled: () => { setConfirmBulkDelete(false); setSelected(new Set()); },
            })
          }
        >
          {bulkDocs.length === 1 ? <span className="font-medium text-foreground">{bulkDocs[0].title}</span> : <>{bulkDocs.length} tài liệu đã chọn</>} cùng toàn bộ đoạn đã index sẽ bị xoá. Trợ lý không tra cứu được nữa và không khôi phục được.
        </ConfirmDialog>
      ) : null}
    </div>
  );
}
