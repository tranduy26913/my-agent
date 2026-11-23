import { useEffect, useRef, useState, type ReactNode } from "react";
import { X } from "lucide-react";

const EXIT_MS = 350; // phải khớp duration-350 ở dưới

/** Giữ khối trong DOM đủ lâu để chạy hoạt ảnh đóng. Chỉ dùng API có ở React 18. */
function usePresence(open: boolean) {
  const [mounted, setMounted] = useState(open);
  const [entered, setEntered] = useState(false);
  if (open && !mounted) setMounted(true);

  useEffect(() => {
    if (open) {
      // Chờ hai khung hình để trình duyệt vẽ trạng thái đầu (ngoài màn) rồi mới trượt vào
      const raf = requestAnimationFrame(() => requestAnimationFrame(() => setEntered(true)));
      return () => cancelAnimationFrame(raf);
    }
    const timer = setTimeout(() => {
      setMounted(false);
      setEntered(false);
    }, EXIT_MS);
    return () => clearTimeout(timer);
  }, [open]);

  return { mounted, shown: open && entered };
}

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title: string;
  /** Dòng phụ dưới tiêu đề */
  subtitle?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
}

/**
 * Panel trượt từ phải. Vào 500ms, ra 350ms, chỉ translate.
 * Lớp phủ nhạt (bg-black/15) để vẫn thấy danh sách phía sau.
 */
export function Drawer({ open, onClose, title, subtitle, children, footer }: DrawerProps) {
  const { mounted, shown } = usePresence(open);
  const panelRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!open) return;
    panelRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!mounted) return null;

  const ease = "ease-[cubic-bezier(0.32,0.72,0,1)] motion-reduce:transition-none";
  return (
    <>
      <div
        onClick={onClose}
        aria-hidden
        className={`fixed inset-0 z-30 bg-black/15 transition-opacity ${ease} ${
          shown ? "opacity-100 duration-500" : "opacity-0 duration-350"
        }`}
      />
      <aside
        ref={panelRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`fixed inset-y-0 right-0 z-40 flex w-full flex-col border-l border-p-line bg-p-surface text-p-fg shadow-p-modal outline-hidden transition-transform sm:w-[34rem] ${ease} ${
          shown ? "translate-x-0 duration-500" : "translate-x-full duration-350"
        }`}
      >
        <div className="flex items-start gap-3 px-6 pb-4 pt-5">
          <div className="min-w-0 flex-1">
            <h2 className="text-pretty text-lg font-semibold">{title}</h2>
            {subtitle ? <div className="mt-0.5 text-sm text-p-muted">{subtitle}</div> : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Đóng"
            className="inline-flex size-8 shrink-0 cursor-pointer items-center justify-center rounded-lg text-p-muted hover:bg-p-fg/5 hover:text-p-fg"
          >
            <X className="size-5" />
          </button>
        </div>
        <div className="flex min-h-0 flex-1 flex-col">{children}</div>
        {footer ? (
          <div className="flex flex-col-reverse gap-2 border-t border-p-line px-6 py-4 sm:flex-row sm:justify-end">{footer}</div>
        ) : null}
      </aside>
    </>
  );
}
