import { LoaderCircle, TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import type { DocStatus } from "../types";
import { STATUS_META } from "../labels";

export function StatusBadge({ status, className }: { status: DocStatus; className?: string }) {
  const meta = STATUS_META[status];
  return (
    <Badge variant="secondary" className={cn(meta.cls, className)}>
      {status === "processing" ? <LoaderCircle className="animate-spin motion-reduce:animate-none" /> : null}
      {meta.label}
    </Badge>
  );
}

export function Field({ label, required, hint, htmlFor, children }: { label: string; required?: boolean; hint?: string; htmlFor?: string; children: ReactNode }) {
  return (
    <div className="grid gap-1.5">
      <Label htmlFor={htmlFor}>
        {label} {required ? <span className="text-destructive">*</span> : null}
      </Label>
      {children}
      {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

/** Chip bật / tắt dùng cho chọn phòng ban, vai trò */
export function ToggleChip({ on, onToggle, children }: { on: boolean; onToggle: () => void; children: ReactNode }) {
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      aria-pressed={on}
      onClick={onToggle}
      className={cn("h-8 px-3 text-sm", on && "border-transparent bg-foreground/8 font-medium hover:bg-foreground/8")}
    >
      {children}
    </Button>
  );
}

export function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <Alert variant="destructive" className="flex items-center gap-3 border-0 bg-destructive/10 px-4 py-3">
      <TriangleAlert className="size-4 shrink-0" />
      <p className="min-w-0 flex-1 text-sm">{message}</p>
      {onRetry ? (
        <Button type="button" variant="link" size="sm" onClick={onRetry} className="h-auto shrink-0 p-0 text-destructive">
          Thử lại
        </Button>
      ) : null}
    </Alert>
  );
}
