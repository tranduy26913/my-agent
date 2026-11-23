import { useEffect, type ReactNode } from "react";
import { Trash2 } from "lucide-react";
import { btn } from "./ui";

interface ConfirmDialogProps {
  title: string;
  /** Hậu quả cụ thể, có tên đối tượng */
  children: ReactNode;
  confirmLabel: string;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/** Hộp xác nhận việc nguy hiểm (xoá). Đỏ, tiêu đề là câu hỏi, nút nói đúng việc. */
export function ConfirmDialog({ title, children, confirmLabel, busy, onConfirm, onCancel }: ConfirmDialogProps) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onCancel();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onCancel]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" onClick={onCancel}>
      <div
        role="alertdialog"
        aria-labelledby="kb-confirm-title"
        aria-describedby="kb-confirm-desc"
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md rounded-2xl border border-kb-line bg-kb-surface p-6 text-kb-fg shadow-kb-modal"
      >
        <div className="grid grid-cols-[auto_minmax(0,1fr)] items-center gap-x-4">
          <div className="flex size-10 items-center justify-center rounded-full bg-kb-danger-bg">
            <Trash2 className="size-5 text-kb-danger" />
          </div>
          <h2 id="kb-confirm-title" className="text-lg font-semibold">{title}</h2>
          <div id="kb-confirm-desc" className="col-span-2 mt-2 text-sm/6 text-kb-muted sm:col-span-1 sm:col-start-2 sm:mt-0.5">
            {children}
          </div>
        </div>
        <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <button type="button" onClick={onCancel} className={`${btn.base} ${btn.secondary} min-h-10`}>Huỷ</button>
          <button type="button" onClick={onConfirm} disabled={busy} className={`${btn.base} ${btn.danger} min-h-10`}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  );
}
