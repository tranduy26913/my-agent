import type { ReactNode } from "react";
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title: string;
  /** Dòng phụ dưới tiêu đề */
  subtitle?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
}

/** Panel trượt từ phải, dựng trên Sheet của shadcn (Radix Dialog: bẫy phím Tab, đóng bằng Esc, trả focus). */
export function Drawer({ open, onClose, title, subtitle, children, footer }: DrawerProps) {
  return (
    <Sheet open={open} onOpenChange={(next) => !next && onClose()}>
      <SheetContent side="right" className="w-full gap-0 p-0 data-[side=right]:sm:max-w-[34rem]">
        <SheetHeader className="px-6 pb-4 pt-5 pr-14">
          <SheetTitle className="text-pretty text-lg font-semibold">{title}</SheetTitle>
          {subtitle ? (
            <SheetDescription asChild>
              <div className="text-sm text-muted-foreground">{subtitle}</div>
            </SheetDescription>
          ) : (
            <SheetDescription className="sr-only">{title}</SheetDescription>
          )}
        </SheetHeader>
        <div className="flex min-h-0 flex-1 flex-col">{children}</div>
        {footer ? <SheetFooter className="flex-col-reverse gap-2 border-t px-6 py-4 sm:flex-row sm:justify-end">{footer}</SheetFooter> : null}
      </SheetContent>
    </Sheet>
  );
}
