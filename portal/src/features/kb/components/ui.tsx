import { LoaderCircle, TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";
import type { DocStatus } from "../types";
import { STATUS_META } from "../labels";

/** Bốn dạng nút của hệ thiết kế. Ghép với h-10 (hoặc h-9 cho nút nhỏ). */
export const btn = {
  base: "inline-flex cursor-pointer items-center justify-center gap-2 rounded-xl px-4 text-sm font-medium transition-colors outline-hidden disabled:cursor-not-allowed disabled:opacity-50",
  outline: "border border-p-line-strong bg-p-surface text-p-fg hover:bg-p-button-hover",
  primary: "bg-p-primary text-p-on-primary hover:bg-p-primary-hover",
  secondary: "bg-p-secondary text-p-fg hover:bg-p-secondary-hover",
  danger: "bg-p-danger-bg text-p-danger hover:bg-p-danger-bg-hover",
};

export const inputCls =
  "h-10 w-full rounded-xl border border-p-line-strong bg-p-surface px-3 text-sm text-p-fg outline-hidden placeholder:text-p-muted focus:border-p-primary focus:ring-2 focus:ring-p-primary/15";

export function StatusBadge({ status, className = "" }: { status: DocStatus; className?: string }) {
  const meta = STATUS_META[status];
  return (
    <span className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${meta.cls} ${className}`}>
      {status === "processing" ? <LoaderCircle className="size-3 animate-spin motion-reduce:animate-none" /> : null}
      {meta.label}
    </span>
  );
}

export function Field({ label, required, hint, htmlFor, children }: { label: string; required?: boolean; hint?: string; htmlFor?: string; children: ReactNode }) {
  return (
    <div className="grid gap-1.5">
      <label htmlFor={htmlFor} className="text-sm font-medium">
        {label} {required ? <span className="text-p-err">*</span> : null}
      </label>
      {children}
      {hint ? <p className="text-xs text-p-muted">{hint}</p> : null}
    </div>
  );
}

/** Chip bật / tắt dùng cho chọn phòng ban, vai trò */
export function ToggleChip({ on, onToggle, children }: { on: boolean; onToggle: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onToggle}
      className={`h-8 cursor-pointer rounded-lg border px-3 text-sm outline-hidden transition-colors ${
        on ? "border-transparent bg-p-tab-selected font-medium text-p-fg" : "border-p-line-strong bg-p-surface text-p-fg/70 hover:bg-p-button-hover"
      }`}
    >
      {children}
    </button>
  );
}

export function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex items-center gap-3 rounded-xl bg-p-err-bg px-4 py-3 text-sm text-p-err">
      <TriangleAlert className="size-4 shrink-0" />
      <p className="min-w-0 flex-1">{message}</p>
      {onRetry ? (
        <button type="button" onClick={onRetry} className="shrink-0 cursor-pointer font-medium underline underline-offset-2">
          Thử lại
        </button>
      ) : null}
    </div>
  );
}
