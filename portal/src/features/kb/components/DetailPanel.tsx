import { Fragment, useState, type ReactNode } from "react";
import { FileUp, Pencil, ShieldCheck, ShieldX } from "lucide-react";
import { useKbHost } from "../host";
import { isBusy, useDocument, useKbMutations } from "../hooks";
import { fmtDate, fmtDateTime } from "../format";
import { VISIBILITY_META, docTypeLabel } from "../labels";
import type { AccessCheck, KbDocumentDetail } from "../types";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Item, ItemContent, ItemDescription, ItemGroup, ItemSeparator, ItemTitle } from "@/components/ui/item";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ConfirmDialog } from "./ConfirmDialog";
import { Drawer } from "./Drawer";
import { ErrorBanner, StatusBadge } from "./ui";

type Tab = "info" | "chunks" | "history";

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <>
      <dt className="text-muted-foreground">{label}</dt>
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
    <Card className="mt-6 gap-3 bg-background">
      <CardHeader>
        <CardTitle className="text-sm font-medium">Kiểm tra quyền đọc</CardTitle>
        <CardDescription>Nhập email để xem người đó có đọc được văn bản này không, theo đúng luật lọc của trợ lý</CardDescription>
      </CardHeader>
      <CardContent>
      <form onSubmit={(e) => { e.preventDefault(); void run(); }} className="flex gap-2">
        <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="ten@saoviet.vn" aria-label="Email nhân viên" className="h-10 min-w-0 flex-1 bg-card" />
        <Button type="submit" variant="outline" size="lg" disabled={busy || !email.trim()} className="h-10 shrink-0 px-3">Kiểm tra</Button>
      </form>
      {result ? (
        <Alert className={`mt-3 border-0 ${result.allowed ? "bg-success/10 text-success" : "bg-destructive/10 text-destructive"}`}>
          {result.allowed ? <ShieldCheck /> : <ShieldX />}
          <AlertDescription className="text-current">
            <span className="font-medium">{result.person ? `${result.person}: ` : ""}{result.allowed ? "Đọc được" : "Không đọc được"}.</span> {result.reason}
          </AlertDescription>
        </Alert>
      ) : null}
      {error ? <p className="mt-3 text-sm text-destructive">{error}</p> : null}
      </CardContent>
    </Card>
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
          <span className="inline-flex items-center gap-1.5"><vis.Icon className="size-4 text-muted-foreground" />{vis.label}{d.classified ? <Badge variant="secondary" className="rounded-md bg-muted text-muted-foreground">Mật</Badge> : null}</span>
          {d.allowedDepartments.length || d.allowedRoles.length ? (
            <span className="mt-1 block text-muted-foreground">
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
        <Row label="Nguồn"><span className="break-all text-muted-foreground">{d.source}</span></Row>
        <Row label="Nạp lúc">{fmtDateTime(d.createdAt)}{d.uploadedBy ? ` · ${d.uploadedBy}` : ""}</Row>
      </dl>
      <AccessChecker docId={d.docId} />
    </div>
  );
}

function ChunksTab({ d }: { d: KbDocumentDetail }) {
  if (d.chunks.length === 0) {
    return <p className="px-6 py-10 text-center text-sm text-muted-foreground">{d.status === "processing" ? "Đang xử lý, chưa có đoạn nào" : "Chưa có đoạn nào được index"}</p>;
  }
  return (
    <div className="px-6 py-5">
      {d.accessLogged ? <p className="mb-3 rounded-lg bg-muted px-3 py-2 text-sm text-muted-foreground">Văn bản Mật: lượt xem này đã được ghi nhật ký.</p> : null}
      <ItemGroup className="gap-0">
        {d.chunks.map((c, i) => (
          <Fragment key={c.ordinal}>
            {i > 0 ? <ItemSeparator className="my-0" /> : null}
            <Item className="px-0 py-3">
              <ItemContent className="min-w-0 gap-1">
                <div className="flex items-baseline gap-3 text-xs text-muted-foreground">
                  <span className="tabular-nums">#{c.ordinal}</span>
                  <span className="truncate font-medium text-foreground">{c.section || "Không có mục"}</span>
                  {c.page ? <span className="ml-auto shrink-0 tabular-nums">tr. {c.page}</span> : null}
                </div>
                <ItemDescription className="line-clamp-3 text-foreground/80">{c.content}</ItemDescription>
              </ItemContent>
            </Item>
          </Fragment>
        ))}
      </ItemGroup>
      {d.chunkCount > d.chunks.length ? <p className="mt-2 text-sm text-muted-foreground">Còn {d.chunkCount - d.chunks.length} đoạn</p> : null}
    </div>
  );
}

function HistoryTab({ d }: { d: KbDocumentDetail }) {
  return (
    <ItemGroup className="gap-0 px-6 py-3">
      {d.history.map((h, i) => (
        <Fragment key={i}>
          {i > 0 ? <ItemSeparator className="my-0" /> : null}
          <Item className="px-0 py-3">
            <ItemContent className="gap-0.5">
              <ItemTitle className="font-normal">{h.text}</ItemTitle>
              <ItemDescription className="text-xs">{fmtDateTime(h.at)} · {h.by}</ItemDescription>
            </ItemContent>
          </Item>
        </Fragment>
      ))}
    </ItemGroup>
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
              <Button type="button" size="lg" variant={quarantined ? "secondary" : "destructive"} disabled={isBusy(quarantine)} onClick={() => quarantine.mutate({ docId: data.docId, on: !quarantined })} className="min-h-10 px-4">
                {quarantined ? "Bỏ cách ly" : "Cách ly"}
              </Button>
              <Button type="button" size="lg" variant="destructive" onClick={() => setConfirmDelete(true)} className="min-h-10 px-4">Gỡ khỏi kho</Button>
            </>
          ) : undefined
        }
      >
        <div className="min-h-0 flex-1 overflow-y-auto">
          {error ? (
            <div className="px-6 py-4"><ErrorBanner message={error instanceof Error ? error.message : "Không tải được tài liệu"} onRetry={() => void refetch()} /></div>
          ) : null}
          {isLoading ? <Skeleton className="mx-6 mt-4 h-24 rounded-xl" /> : null}
          {data ? (
            <>
              <div className="px-6">
                {data.statusNote ? <p className="mb-3 text-sm text-muted-foreground">{data.statusNote}</p> : null}
                {quarantine.error || reindex.error || remove.error ? (
                  <div className="mb-3"><ErrorBanner message={((quarantine.error ?? reindex.error ?? remove.error) as Error).message || "Thao tác không thành công"} /></div>
                ) : null}
                <div className="flex gap-2">
                  <Button type="button" variant="outline" size="lg" disabled title="Chưa nối API" className="px-3"><Pencil />Sửa thông tin</Button>
                  <Button type="button" variant="outline" size="lg" disabled title="Chưa nối API" className="px-3"><FileUp />Thay bản mới</Button>
                  <Button type="button" variant="outline" size="lg" disabled={isBusy(reindex)} onClick={() => reindex.mutate([data.docId])} className="px-3">Nạp lại</Button>
                </div>
              </div>

              <Tabs
                value={activeTab}
                onValueChange={(v) => setTab({ docId: shownId, value: v as Tab })}
                className="sticky top-0 z-10 mt-5 gap-0 border-b bg-card px-6"
              >
                <TabsList variant="line" className="h-10 gap-2 p-0">
                  {tabs.map((t) => (
                    <TabsTrigger key={t.id} value={t.id} className="flex-none px-2">
                      {t.label}{t.count !== undefined ? <span className="ml-1 tabular-nums text-muted-foreground">{t.count}</span> : null}
                    </TabsTrigger>
                  ))}
                </TabsList>
              </Tabs>

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
          <span className="font-medium text-foreground">{data.title}</span> cùng {data.chunkCount} đoạn đã index sẽ bị xoá. Trợ lý không tra cứu được nữa và không khôi phục được.
        </ConfirmDialog>
      ) : null}
    </>
  );
}
