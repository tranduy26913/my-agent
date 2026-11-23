import { Construction } from "lucide-react";
import { findNavItem } from "./nav";

/** Trang tạm cho mục đã có trong nav.ts nhưng chưa làm. Đọc mô tả từ nav.ts để khỏi viết hai nơi. */
export function ComingSoon({ href, note }: { href: string; note?: string }) {
  const item = findNavItem(href);
  return (
    <div className="mx-auto mt-10 flex max-w-md flex-col items-center rounded-2xl bg-p-surface px-6 py-12 text-center">
      <span className="flex size-12 items-center justify-center rounded-full bg-p-warn-bg text-p-warn">
        <Construction className="size-6" />
      </span>
      <h2 className="mt-4 text-base font-semibold">{item?.label ?? "Trang này"} đang được phát triển</h2>
      {item && <p className="mt-1 text-sm text-p-muted">{item.description}</p>}
      {note && <p className="mt-3 text-xs text-p-muted">{note}</p>}
    </div>
  );
}
