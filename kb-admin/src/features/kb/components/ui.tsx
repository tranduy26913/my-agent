import { LoaderCircle, TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";
import type { DocStatus } from "../types";
import { STATUS_META } from "../labels";

/** Bốn dạng nút của hệ thiết kế. Ghép với h-10 (hoặc h-9 cho nút nhỏ). */
export const btn = {
  base: "inline-flex cursor-pointer items-center justify-center gap-2 rounded-xl px-4 text-sm font-medium transition-colors outline-hidden disabled:cursor-not-allowed disabled:opacity-50",
  outline: "border border-kb-line-strong bg-kb-surface text-kb-fg hover:bg-kb-button-hover",
  primary: "bg-kb-primary text-kb-on-primary hover:bg-kb-primary-hover",
  secondary: "bg-kb-secondary text-kb-fg hover:bg-kb-secondary-hover",
  danger: "bg-kb-danger-bg text-kb-danger hover:bg-kb-danger-bg-hover",
};

export const inputCls =
  "h-10 w-full rounded-xl border border-kb-line-strong bg-kb-surface px-3 text-sm text-kb-fg outline-hidden placeholder:text-kb-muted focus:border-kb-primary focus:ring-2 focus:ring-kb-primary/15";

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
        {label} {required ? <span className="text-kb-err">*</span> : null}
      </label>
      {children}
      {hint ? <p className="text-xs text-kb-muted">{hint}</p> : null}
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
        on ? "border-transparent bg-kb-tab-selected font-medium text-kb-fg" : "border-kb-line-strong bg-kb-surface text-kb-fg/70 hover:bg-kb-button-hover"
      }`}
    >
      {children}
    </button>
  );
}

export function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex items-center gap-3 rounded-xl bg-kb-err-bg px-4 py-3 text-sm text-kb-err">
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
