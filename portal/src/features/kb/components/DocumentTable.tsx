import { File as FileIcon, FileImage, FileText } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { KbDocument } from "../types";
import { fmtDate } from "../format";
import { VISIBILITY_META } from "../labels";
import { StatusBadge } from "./ui";

function FileKindIcon({ kind }: { kind: KbDocument["fileKind"] }) {
  const cls = "mt-0.5 size-5 shrink-0 text-muted-foreground sm:mt-0";
  if (kind === "image") return <FileImage className={cls} />;
  if (kind === "other") return <FileIcon className={cls} />;
  return <FileText className={cls} />;
}

function noteColor(status: KbDocument["status"]) {
  return status === "error" ? "text-destructive" : status === "quarantined" ? "text-warning" : "";
}

function effectiveText(d: KbDocument) {
  if (d.status === "processing" || d.status === "error") return <span className="text-muted-foreground">—</span>;
  if (d.effectiveTo) return <span className="text-muted-foreground">Hết từ {fmtDate(d.effectiveTo)}</span>;
  return d.effectiveFrom ? <>Từ {fmtDate(d.effectiveFrom)}</> : <span className="text-muted-foreground">—</span>;
}

interface Props {
  rows: KbDocument[];
  loading: boolean;
  selected: Set<string>;
  onToggle(docId: string): void;
  onToggleAll(checked: boolean): void;
  onOpen(docId: string): void;
  emptyText: string;
}

export function DocumentTable({ rows, loading, selected, onToggle, onToggleAll, onOpen, emptyText }: Props) {
  const allChecked = rows.length > 0 && rows.every((r) => selected.has(r.docId));
  const someChecked = rows.some((r) => selected.has(r.docId));

  return (
    <Table className="table-fixed">
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          <TableHead className="w-12 pl-2">
            {/* Không có dòng nào thì ẩn ô chọn, giữ chỗ để cột không xê dịch */}
            <div className={`flex size-8 items-center justify-center ${rows.length ? "" : "invisible"}`}>
              <Checkbox
                aria-label="Chọn tất cả"
                checked={allChecked ? true : someChecked ? "indeterminate" : false}
                onCheckedChange={(v) => onToggleAll(v === true)}
              />
            </div>
          </TableHead>
          <TableHead className="text-xs text-muted-foreground">Tài liệu</TableHead>
          <TableHead className="hidden w-24 text-xs text-muted-foreground @3xl:table-cell">Phòng</TableHead>
          <TableHead className="hidden w-56 text-xs text-muted-foreground @2xl:table-cell">Phạm vi xem</TableHead>
          <TableHead className="hidden w-40 text-xs text-muted-foreground @4xl:table-cell">Hiệu lực</TableHead>
          <TableHead className="hidden w-32 text-xs text-muted-foreground sm:table-cell">Trạng thái</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {loading
          ? Array.from({ length: 6 }, (_, i) => (
              <TableRow key={i} aria-hidden className="hover:bg-transparent">
                <TableCell className="pl-2"><div className="size-8" /></TableCell>
                <TableCell className="py-4"><Skeleton className="h-4 w-2/3" /><Skeleton className="mt-2 h-3 w-1/3" /></TableCell>
                <TableCell className="hidden @3xl:table-cell" />
                <TableCell className="hidden @2xl:table-cell" />
                <TableCell className="hidden @4xl:table-cell" />
                <TableCell className="hidden sm:table-cell" />
              </TableRow>
            ))
          : null}

        {!loading && rows.length === 0 ? (
          <TableRow className="hover:bg-transparent">
            <TableCell colSpan={6} className="py-10 text-center text-sm text-muted-foreground">{emptyText}</TableCell>
          </TableRow>
        ) : null}

        {!loading &&
          rows.map((d) => {
            const vis = VISIBILITY_META[d.visibility];
            const sub = d.statusNote ? (
              <span className={noteColor(d.status)}>{d.statusNote}</span>
            ) : (
              <>{d.docId}{d.soHieu ? ` · ${d.soHieu}` : ""}</>
            );
            return (
              <TableRow
                key={d.docId}
                tabIndex={0}
                aria-label={`Mở ${d.title}`}
                data-state={selected.has(d.docId) ? "selected" : undefined}
                className="cursor-pointer outline-none focus-visible:bg-muted/50"
                onClick={() => onOpen(d.docId)}
                onKeyDown={(e) => {
                  if (e.target === e.currentTarget && (e.key === "Enter" || e.key === " ")) {
                    e.preventDefault();
                    onOpen(d.docId);
                  }
                }}
              >
                <TableCell className="pl-2 align-top sm:align-middle" onClick={(e) => e.stopPropagation()}>
                  <div className="flex size-8 items-center justify-center">
                    <Checkbox
                      aria-label={`Chọn ${d.title}`}
                      checked={selected.has(d.docId)}
                      onCheckedChange={() => onToggle(d.docId)}
                    />
                  </div>
                </TableCell>
                <TableCell className="whitespace-normal py-3 pr-2 sm:pr-4">
                  <div className="flex min-w-0 items-start gap-3 sm:items-center">
                    <FileKindIcon kind={d.fileKind} />
                    <div className="min-w-0">
                      <p
                        title={d.title}
                        className="line-clamp-2 text-pretty font-medium [overflow-wrap:anywhere] sm:line-clamp-none sm:truncate"
                      >
                        {d.title}
                      </p>
                      <p className="truncate text-xs text-muted-foreground">{sub}</p>
                      <StatusBadge status={d.status} className="mt-2 sm:hidden" />
                    </div>
                  </div>
                </TableCell>
                <TableCell className="hidden truncate py-3 pr-4 @3xl:table-cell" title={d.department}>{d.department}</TableCell>
                <TableCell className="hidden py-3 pr-4 @2xl:table-cell">
                  <div className="flex min-w-0 items-center gap-1.5">
                    <vis.Icon className="size-4 shrink-0 text-muted-foreground" />
                    <span className="truncate" title={[vis.label, ...d.allowedDepartments].join(" · ")}>
                      {vis.label}
                      {d.allowedDepartments.length ? <span className="text-muted-foreground"> · {d.allowedDepartments.join(", ")}</span> : null}
                    </span>
                    {d.classified ? <Badge variant="secondary" className="shrink-0 rounded-md bg-muted text-muted-foreground">Mật</Badge> : null}
                  </div>
                </TableCell>
                <TableCell className="hidden py-3 pr-4 tabular-nums @4xl:table-cell">{effectiveText(d)}</TableCell>
                <TableCell className="hidden py-3 pr-4 sm:table-cell"><StatusBadge status={d.status} /></TableCell>
              </TableRow>
            );
          })}
      </TableBody>
    </Table>
  );
}
