import { useMemo, useState } from "react";
import { ChevronDown, RefreshCw, Search, Trash2, Upload } from "lucide-react";
import { useKbHost } from "../host";
import { isBusy, useDocuments, useKbMutations } from "../hooks";
import { fold } from "../format";
import { STATUS_META, STATUS_ORDER } from "../labels";
import type { DocStatus } from "../types";
import { ConfirmDialog } from "./ConfirmDialog";
import { DetailPanel } from "./DetailPanel";
import { DocumentTable } from "./DocumentTable";
import { UploadPanel } from "./UploadPanel";
import { ErrorBanner, btn, inputCls } from "./ui";

type Filter = "all" | DocStatus;

/**
 * Nội dung trang Kho tri thức: thanh công cụ + bảng + hai panel.
 * KHÔNG gồm sidebar / header: đó là khung của ứng dụng chủ.
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
    <div className="flex flex-col gap-4 text-p-fg">
      {hasSelection ? (
        <div className="flex h-10 items-center gap-3">
          <p className="text-sm font-medium"><span className="tabular-nums">{selectedIds.length}</span> tài liệu đã chọn</p>
          <button type="button" onClick={() => setSelected(new Set())} className="cursor-pointer text-sm font-medium text-p-muted hover:text-p-fg">Bỏ chọn</button>
          <div className="ml-auto flex gap-2">
            <button
              type="button"
              disabled={isBusy(reindex)}
              onClick={() => reindex.mutate(selectedIds, { onSuccess: () => setSelected(new Set()) })}
              className={`${btn.base} ${btn.outline} h-10 px-3`}
            >
              <RefreshCw className="size-4" />Nạp lại
            </button>
            <button type="button" onClick={() => setConfirmBulkDelete(true)} className={`${btn.base} ${btn.danger} h-10 px-3`}>
              <Trash2 className="size-4" />Gỡ khỏi kho
            </button>
          </div>
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-3">
          {/* Dưới sm: tab thành nút chọn có nhãn */}
          <label className="relative inline-flex h-10 w-fit items-center gap-1.5 rounded-xl border border-p-line-strong bg-p-surface pl-3 pr-9 text-sm sm:hidden">
            <span className="text-p-muted">Trạng thái:</span>
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value as Filter)}
              aria-label="Lọc theo trạng thái"
              className="cursor-pointer appearance-none bg-transparent font-medium outline-hidden"
            >
              {tabs.map((t) => <option key={t.id} value={t.id}>{t.label} · {counts[t.id]}</option>)}
            </select>
            <ChevronDown className="pointer-events-none absolute right-3 size-4 text-p-muted" />
          </label>

          <div className="-mx-1 hidden min-w-0 overflow-x-auto py-0.5 [scrollbar-width:none] sm:block [&::-webkit-scrollbar]:hidden">
            <div role="tablist" aria-label="Lọc theo trạng thái" className="flex gap-1 px-1">
              {tabs.map((t) => {
                const on = filter === t.id;
                return (
                  <button
                    key={t.id}
                    role="tab"
                    aria-selected={on}
                    onClick={() => setFilter(t.id)}
                    className={`h-9 shrink-0 cursor-pointer whitespace-nowrap rounded-lg border border-transparent px-3 text-sm font-medium outline-hidden ${
                      on ? "bg-p-tab-selected text-p-fg" : "text-p-fg/70 hover:bg-p-fg/5 hover:text-p-fg"
                    }`}
                  >
                    {t.label} <span className="ml-1 tabular-nums">{counts[t.id]}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="ml-auto flex w-full items-center gap-2 sm:w-auto">
            <label className="relative flex-1 sm:w-64 sm:flex-none">
              <span className="sr-only">Tìm tài liệu</span>
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-p-muted" />
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Tìm theo tên, mã, số hiệu"
                className={`${inputCls} pl-9`}
              />
            </label>
            <button type="button" onClick={() => route.open("upload")} className={`${btn.base} ${btn.primary} h-10 shrink-0`}>
              <Upload className="size-4" />Nạp tài liệu
            </button>
          </div>
        </div>
      )}

      {error ? <ErrorBanner message={error instanceof Error ? error.message : "Không tải được danh sách tài liệu"} onRetry={() => void refetch()} /> : null}
      {/* Backend thật có thể từ chối hoặc xong một phần; thông báo lỗi lấy từ `detail` của API */}
      {mutationError ? <ErrorBanner message={mutationError instanceof Error ? mutationError.message : "Thao tác không thành công"} /> : null}

      <section className="@container overflow-hidden rounded-xl border border-p-line bg-p-surface">
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
          <div className="border-t border-p-line px-4 py-3">
            <p className="text-sm tabular-nums text-p-muted">
              {rows.length === docs.length ? `${docs.length} tài liệu` : `${rows.length} trong ${docs.length} tài liệu`} · {docs.reduce((n, d) => n + d.chunkCount, 0)} đoạn đã index
            </p>
          </div>
        ) : null}
      </section>

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
          {bulkDocs.length === 1 ? <span className="font-medium text-p-fg">{bulkDocs[0].title}</span> : <>{bulkDocs.length} tài liệu đã chọn</>} cùng toàn bộ đoạn đã index sẽ bị xoá. Trợ lý không tra cứu được nữa và không khôi phục được.
        </ConfirmDialog>
      ) : null}
    </div>
  );
}
