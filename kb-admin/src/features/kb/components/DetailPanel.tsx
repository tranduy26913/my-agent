import { useState, type ReactNode } from "react";
import { FileUp, Pencil, ShieldCheck, ShieldX } from "lucide-react";
import { useKbHost } from "../host";
import { isBusy, useDocument, useKbMutations } from "../hooks";
import { fmtDate, fmtDateTime } from "../format";
import { VISIBILITY_META, docTypeLabel } from "../labels";
import type { AccessCheck, KbDocumentDetail } from "../types";
import { ConfirmDialog } from "./ConfirmDialog";
import { Drawer } from "./Drawer";
import { ErrorBanner, StatusBadge, btn, inputCls } from "./ui";

type Tab = "info" | "chunks" | "history";

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <>
      <dt className="text-kb-muted">{label}</dt>
      <dd className="min-w-0 break-words max-sm:mb-2">{children}</dd>
    </>
  );
}

function AccessChecker({ docId }: { docId: string }) {
  const { api } = useKbHost();
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<AccessCheck | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    if (!email.trim()) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await api.checkAccess(docId, email));
    } catch (e) {
      setResult(null);
      setError(e instanceof Error ? e.message : "Không kiểm tra được");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-6 rounded-xl bg-kb-bg p-4">
      <p className="text-sm font-medium">Kiểm tra quyền đọc</p>
      <p className="mt-1 text-sm text-kb-muted">Nhập email để xem người đó có đọc được văn bản này không, theo đúng luật lọc của trợ lý</p>
      <form onSubmit={(e) => { e.preventDefault(); void run(); }} className="mt-3 flex gap-2">
        <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="ten@saoviet.vn" aria-label="Email nhân viên" className={`${inputCls} min-w-0 flex-1`} />
        <button type="submit" disabled={busy || !email.trim()} className={`${btn.base} ${btn.outline} h-10 shrink-0 px-3`}>Kiểm tra</button>
      </form>
      {result ? (
        <div className={`mt-3 flex gap-2 rounded-lg p-3 text-sm ${result.allowed ? "bg-kb-ok-bg text-kb-ok" : "bg-kb-err-bg text-kb-err"}`}>
          {result.allowed ? <ShieldCheck className="mt-0.5 size-4 shrink-0" /> : <ShieldX className="mt-0.5 size-4 shrink-0" />}
          <p>
            <span className="font-medium">{result.person ? `${result.person}: ` : ""}{result.allowed ? "Đọc được" : "Không đọc được"}.</span> {result.reason}
          </p>
        </div>
      ) : null}
      {error ? <p className="mt-3 text-sm text-kb-err">{error}</p> : null}
    </div>
  );
}

function InfoTab({ d }: { d: KbDocumentDetail }) {
  const vis = VISIBILITY_META[d.visibility];
  return (
    <div className="px-6 py-5">
      <dl className="grid grid-cols-1 gap-x-4 gap-y-1 text-sm sm:grid-cols-[7rem_minmax(0,1fr)] sm:gap-y-3">
        <Row label="Loại">{docTypeLabel(d.docType)}</Row>
        <Row label="Phòng sở hữu">{d.department}</Row>
        <Row label="Phạm vi xem">
          <span className="inline-flex items-center gap-1.5"><vis.Icon className="size-4 text-kb-muted" />{vis.label}{d.classified ? <span className="rounded-md bg-kb-neutral-bg px-1.5 py-0.5 text-xs font-medium text-kb-neutral">Mật</span> : null}</span>
          {d.allowedDepartments.length || d.allowedRoles.length ? (
            <span className="mt-1 block text-kb-muted">
              {d.allowedDepartments.length ? `Phòng: ${d.allowedDepartments.join(", ")}` : null}
              {d.allowedDepartments.length && d.allowedRoles.length ? " · " : null}
              {d.allowedRoles.length ? `Vai trò: ${d.allowedRoles.join(", ")}` : null}
            </span>
          ) : null}
        </Row>
        <Row label="Hiệu lực">
          {d.effectiveFrom ? `Từ ${fmtDate(d.effectiveFrom)}` : "—"}{d.effectiveTo ? `, hết ${fmtDate(d.effectiveTo)}` : d.effectiveFrom ? ", chưa có ngày hết" : ""}
        </Row>
        {d.supersedes ? <Row label="Thay thế"><span className="font-medium">{d.supersedes}</span></Row> : null}
        {d.supersededBy ? <Row label="Bị thay bởi"><span className="font-medium">{d.supersededBy}</span></Row> : null}
        <Row label="Phiên bản">{d.version ?? "—"}</Row>
        <Row label="Nguồn"><span className="break-all text-kb-muted">{d.source}</span></Row>
        <Row label="Nạp lúc">{fmtDateTime(d.createdAt)}{d.uploadedBy ? ` · ${d.uploadedBy}` : ""}</Row>
      </dl>
      <AccessChecker docId={d.docId} />
    </div>
  );
}

function ChunksTab({ d }: { d: KbDocumentDetail }) {
  if (d.chunks.length === 0) {
    return <p className="px-6 py-10 text-center text-sm text-kb-muted">{d.status === "processing" ? "Đang xử lý, chưa có đoạn nào" : "Chưa có đoạn nào được index"}</p>;
  }
  return (
    <div className="px-6 py-5">
      {d.accessLogged ? <p className="mb-3 rounded-lg bg-kb-neutral-bg px-3 py-2 text-sm text-kb-neutral">Văn bản Mật: lượt xem này đã được ghi nhật ký.</p> : null}
      <ol className="divide-y divide-kb-line">
        {d.chunks.map((c) => (
          <li key={c.ordinal} className="py-3 first:pt-0">
            <div className="flex items-baseline gap-3 text-xs text-kb-muted">
              <span className="tabular-nums">#{c.ordinal}</span>
              <span className="truncate font-medium text-kb-fg">{c.section || "Không có mục"}</span>
              {c.page ? <span className="ml-auto shrink-0 tabular-nums">tr. {c.page}</span> : null}
            </div>
            <p className="mt-1 line-clamp-3 text-sm text-kb-fg/80">{c.content}</p>
          </li>
        ))}
      </ol>
      {d.chunkCount > d.chunks.length ? <p className="mt-2 text-sm text-kb-muted">Còn {d.chunkCount - d.chunks.length} đoạn</p> : null}
    </div>
  );
}

function HistoryTab({ d }: { d: KbDocumentDetail }) {
  return (
    <ol className="grid gap-4 px-6 py-5 text-sm">
      {d.history.map((h, i) => (
        <li key={i}>
          <p>{h.text}</p>
          <p className="text-xs text-kb-muted">{fmtDateTime(h.at)} · {h.by}</p>
        </li>
      ))}
    </ol>
  );
}

interface Props {
  open: boolean;
  docId: string | null;
  onClose: () => void;
}

export function DetailPanel({ open, docId, onClose }: Props) {
  // Giữ tài liệu cuối cùng để nội dung không biến mất trong lúc panel đang trượt ra
  const [lastId, setLastId] = useState(docId);
  if (docId && docId !== lastId) setLastId(docId);
  const shownId = docId ?? lastId;

  const { data, isLoading, error, refetch } = useDocument(shownId);
  const { reindex, quarantine, remove } = useKbMutations();
  const [tab, setTab] = useState<{ docId: string | null; value: Tab }>({ docId: shownId, value: "info" });
  const [confirmDelete, setConfirmDelete] = useState(false);

  const activeTab: Tab = tab.docId === shownId ? tab.value : "info";
  const tabs: { id: Tab; label: string; count?: number }[] = [
    { id: "info", label: "Thông tin" },
    { id: "chunks", label: "Các đoạn", count: data?.chunkCount },
    { id: "history", label: "Lịch sử" },
  ];

  const quarantined = data?.status === "quarantined";

  return (
    <>
      <Drawer
        open={open}
        onClose={onClose}
        title={data?.title ?? (error ? "Không mở được tài liệu" : "Đang tải…")}
        subtitle={
          data ? (
            <span className="flex flex-wrap items-center gap-2">
              <StatusBadge status={data.status} />
              <span>{data.docId}{data.soHieu ? ` · ${data.soHieu}` : ""}</span>
            </span>
          ) : undefined
        }
        footer={
          data ? (
            <>
              <button type="button" disabled={isBusy(quarantine)} onClick={() => quarantine.mutate({ docId: data.docId, on: !quarantined })} className={`${btn.base} ${quarantined ? btn.secondary : btn.danger} min-h-10`}>
                {quarantined ? "Bỏ cách ly" : "Cách ly"}
              </button>
              <button type="button" onClick={() => setConfirmDelete(true)} className={`${btn.base} ${btn.danger} min-h-10`}>Gỡ khỏi kho</button>
            </>
          ) : undefined
        }
      >
        <div className="min-h-0 flex-1 overflow-y-auto">
          {error ? (
            <div className="px-6 py-4"><ErrorBanner message={error instanceof Error ? error.message : "Không tải được tài liệu"} onRetry={() => void refetch()} /></div>
          ) : null}
          {isLoading ? <div className="mx-6 mt-4 h-24 animate-pulse rounded-xl bg-kb-fg/5 motion-reduce:animate-none" /> : null}
          {data ? (
            <>
              <div className="px-6">
                {data.statusNote ? <p className="mb-3 text-sm text-kb-muted">{data.statusNote}</p> : null}
                {quarantine.error || reindex.error || remove.error ? (
                  <div className="mb-3"><ErrorBanner message={((quarantine.error ?? reindex.error ?? remove.error) as Error).message || "Thao tác không thành công"} /></div>
                ) : null}
                <div className="flex gap-2">
                  <button type="button" disabled className={`${btn.base} ${btn.outline} h-9 rounded-lg px-3`} title="Chưa nối API"><Pencil className="size-4" />Sửa thông tin</button>
                  <button type="button" disabled className={`${btn.base} ${btn.outline} h-9 rounded-lg px-3`} title="Chưa nối API"><FileUp className="size-4" />Thay bản mới</button>
                  <button type="button" disabled={isBusy(reindex)} onClick={() => reindex.mutate([data.docId])} className={`${btn.base} ${btn.outline} h-9 rounded-lg px-3`}>Nạp lại</button>
                </div>
              </div>

              <div className="sticky top-0 z-10 mt-5 bg-kb-surface px-6">
                <div role="tablist" className="flex gap-2 shadow-[inset_0_-1px_0_color-mix(in_srgb,var(--kb-fg)_10%,transparent)]">
                  {tabs.map((t) => {
                    const on = activeTab === t.id;
                    return (
                      <button
                        key={t.id}
                        role="tab"
                        aria-selected={on}
                        onClick={() => setTab({ docId: shownId, value: t.id })}
                        className={`relative box-content h-10 cursor-pointer px-2 pb-px text-sm font-medium outline-hidden after:absolute after:inset-x-2 after:bottom-0 after:h-0.5 after:rounded-full ${
                          on ? "text-kb-fg after:bg-kb-fg" : "text-kb-fg/70 after:bg-transparent hover:text-kb-fg"
                        }`}
                      >
                        {t.label}{t.count !== undefined ? <span className="ml-1 tabular-nums text-kb-muted">{t.count}</span> : null}
                      </button>
                    );
                  })}
                </div>
              </div>

              {activeTab === "info" ? <InfoTab d={data} /> : null}
              {activeTab === "chunks" ? <ChunksTab d={data} /> : null}
              {activeTab === "history" ? <HistoryTab d={data} /> : null}
            </>
          ) : null}
        </div>
      </Drawer>

      {confirmDelete && data ? (
        <ConfirmDialog
          title="Gỡ tài liệu khỏi kho?"
          confirmLabel="Gỡ khỏi kho"
          busy={isBusy(remove)}
          onCancel={() => setConfirmDelete(false)}
          onConfirm={() => remove.mutate([data.docId], { onSuccess: () => { setConfirmDelete(false); onClose(); } })}
        >
          <span className="font-medium text-kb-fg">{data.title}</span> cùng {data.chunkCount} đoạn đã index sẽ bị xoá. Trợ lý không tra cứu được nữa và không khôi phục được.
        </ConfirmDialog>
      ) : null}
    </>
  );
}
