import { File as FileIcon, FileImage, FileText } from "lucide-react";
import type { KbDocument } from "../types";
import { fmtDate } from "../format";
import { VISIBILITY_META } from "../labels";
import { StatusBadge } from "./ui";

function FileKindIcon({ kind }: { kind: KbDocument["fileKind"] }) {
  const cls = "mt-0.5 size-5 shrink-0 text-p-muted sm:mt-0";
  if (kind === "image") return <FileImage className={cls} />;
  if (kind === "other") return <FileIcon className={cls} />;
  return <FileText className={cls} />;
}

function noteColor(status: KbDocument["status"]) {
  return status === "error" ? "text-p-err" : status === "quarantined" ? "text-p-warn" : "";
}

function effectiveText(d: KbDocument) {
  if (d.status === "processing" || d.status === "error") return <span className="text-p-muted">—</span>;
  if (d.effectiveTo) return <span className="text-p-muted">Hết từ {fmtDate(d.effectiveTo)}</span>;
  return d.effectiveFrom ? <>Từ {fmtDate(d.effectiveFrom)}</> : <span className="text-p-muted">—</span>;
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
    <table className="w-full table-fixed text-sm">
      <thead className="border-b border-p-line text-left text-xs font-medium text-p-muted">
        <tr>
          <th className="w-12 py-1 pl-2">
            {/* Không có dòng nào thì ẩn ô chọn, giữ chỗ để cột không xê dịch */}
            <label className={`flex size-8 items-center justify-center ${rows.length ? "cursor-pointer" : "invisible"}`}>
              <input
                type="checkbox"
                aria-label="Chọn tất cả"
                checked={allChecked}
                ref={(el) => {
                  if (el) el.indeterminate = someChecked && !allChecked;
                }}
                onChange={(e) => onToggleAll(e.target.checked)}
                className="size-4 accent-p-primary"
              />
            </label>
          </th>
          <th className="py-3 pr-4 font-medium">Tài liệu</th>
          <th className="hidden w-24 whitespace-nowrap py-3 pr-4 font-medium @3xl:table-cell">Phòng</th>
          <th className="hidden w-56 py-3 pr-4 font-medium @2xl:table-cell">Phạm vi xem</th>
          <th className="hidden w-40 py-3 pr-4 font-medium @4xl:table-cell">Hiệu lực</th>
          <th className="hidden w-32 py-3 pr-4 font-medium sm:table-cell">Trạng thái</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-p-line">
        {loading
          ? Array.from({ length: 6 }, (_, i) => (
              <tr key={i} aria-hidden>
                <td className="py-2 pl-2"><div className="size-8" /></td>
                <td className="py-4 pr-4"><div className="h-4 w-2/3 animate-pulse rounded bg-p-fg/5 motion-reduce:animate-none" /><div className="mt-2 h-3 w-1/3 animate-pulse rounded bg-p-fg/5 motion-reduce:animate-none" /></td>
                <td className="hidden @3xl:table-cell" />
                <td className="hidden @2xl:table-cell" />
                <td className="hidden @4xl:table-cell" />
                <td className="hidden sm:table-cell" />
              </tr>
            ))
          : null}

        {!loading && rows.length === 0 ? (
          <tr>
            <td colSpan={6} className="py-10 text-center text-sm text-p-muted">{emptyText}</td>
          </tr>
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
              <tr
                key={d.docId}
                tabIndex={0}
                aria-label={`Mở ${d.title}`}
                className="cursor-pointer outline-hidden transition-colors hover:bg-p-row-hover has-[:checked]:bg-p-row-hover"
                onClick={() => onOpen(d.docId)}
                onKeyDown={(e) => {
                  if (e.target === e.currentTarget && (e.key === "Enter" || e.key === " ")) {
                    e.preventDefault();
                    onOpen(d.docId);
                  }
                }}
              >
                <td className="py-2 pl-2 align-top sm:align-middle" onClick={(e) => e.stopPropagation()}>
                  <label className="flex size-8 cursor-pointer items-center justify-center">
                    <input
                      type="checkbox"
                      aria-label={`Chọn ${d.title}`}
                      checked={selected.has(d.docId)}
                      onChange={() => onToggle(d.docId)}
                      className="size-4 accent-p-primary"
                    />
                  </label>
                </td>
                <td className="py-3 pr-2 sm:pr-4">
                  <div className="flex min-w-0 items-start gap-3 sm:items-center">
                    <FileKindIcon kind={d.fileKind} />
                    <div className="min-w-0">
                      <p
                        title={d.title}
                        className="line-clamp-2 text-pretty font-medium [overflow-wrap:anywhere] sm:line-clamp-none sm:truncate"
                      >
                        {d.title}
                      </p>
                      <p className="truncate text-xs text-p-muted">{sub}</p>
                      <StatusBadge status={d.status} className="mt-2 sm:hidden" />
                    </div>
                  </div>
                </td>
                <td className="hidden truncate py-3 pr-4 @3xl:table-cell" title={d.department}>{d.department}</td>
                <td className="hidden py-3 pr-4 @2xl:table-cell">
                  <div className="flex min-w-0 items-center gap-1.5">
                    <vis.Icon className="size-4 shrink-0 text-p-muted" />
                    <span className="truncate" title={[vis.label, ...d.allowedDepartments].join(" · ")}>
                      {vis.label}
                      {d.allowedDepartments.length ? <span className="text-p-muted"> · {d.allowedDepartments.join(", ")}</span> : null}
                    </span>
                    {d.classified ? <span className="shrink-0 rounded-md bg-p-neutral-bg px-1.5 py-0.5 text-xs font-medium text-p-neutral">Mật</span> : null}
                  </div>
                </td>
                <td className="hidden whitespace-nowrap py-3 pr-4 tabular-nums @4xl:table-cell">{effectiveText(d)}</td>
                <td className="hidden py-3 pr-4 sm:table-cell"><StatusBadge status={d.status} /></td>
              </tr>
            );
          })}
      </tbody>
    </table>
  );
}
