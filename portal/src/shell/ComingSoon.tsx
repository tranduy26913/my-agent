import { Construction } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { findNavItem } from "./nav";

/** Trang tạm cho mục đã có trong nav.ts nhưng chưa làm. Đọc mô tả từ nav.ts để khỏi viết hai nơi. */
export function ComingSoon({ href, note }: { href: string; note?: string }) {
  const item = findNavItem(href);
  return (
    <Card className="mx-auto mt-10 max-w-md">
      <CardContent className="flex flex-col items-center px-6 py-6 text-center">
        <span className="flex size-12 items-center justify-center rounded-full bg-warning/10 text-warning">
          <Construction className="size-6" />
        </span>
        <h2 className="mt-4 text-base font-semibold">{item?.label ?? "Trang này"} đang được phát triển</h2>
        {item && <p className="mt-1 text-sm text-muted-foreground">{item.description}</p>}
        {note && <p className="mt-3 text-xs text-muted-foreground">{note}</p>}
      </CardContent>
    </Card>
  );
}
