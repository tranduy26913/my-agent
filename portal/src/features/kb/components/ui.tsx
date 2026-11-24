import { TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Field as ShadField, FieldDescription, FieldLabel } from "@/components/ui/field";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";
import type { DocStatus } from "../types";
import { STATUS_META } from "../labels";

export function StatusBadge({ status, className }: { status: DocStatus; className?: string }) {
  const meta = STATUS_META[status];
  return (
    <Badge variant="secondary" className={cn(meta.cls, className)}>
      {status === "processing" ? <Spinner className="size-3 motion-reduce:animate-none" aria-label="Đang xử lý" /> : null}
      {meta.label}
    </Badge>
  );
}

/** Một trường biểu mẫu: nhãn + điều khiển + gợi ý, dựng trên Field của shadcn. */
export function Field({ label, required, hint, htmlFor, children }: { label: string; required?: boolean; hint?: string; htmlFor?: string; children: ReactNode }) {
  return (
    <ShadField className="gap-1.5">
      <FieldLabel htmlFor={htmlFor}>
        {label} {required ? <span className="text-destructive">*</span> : null}
      </FieldLabel>
      {children}
      {hint ? <FieldDescription className="text-xs">{hint}</FieldDescription> : null}
    </ShadField>
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
