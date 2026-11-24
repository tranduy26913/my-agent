import { Construction } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { findNavItem } from "./nav";

/** Trang tạm cho mục đã có trong nav.ts nhưng chưa làm. Đọc mô tả từ nav.ts để khỏi viết hai nơi. */
export function ComingSoon({ href, note }: { href: string; note?: string }) {
  const item = findNavItem(href);
  return (
    <Card className="mx-auto mt-10 max-w-md py-6">
      <Empty className="border-0">
        <EmptyHeader>
          <EmptyMedia variant="icon" className="size-12 rounded-full bg-warning/10 text-warning [&_svg:not([class*='size-'])]:size-6">
            <Construction />
          </EmptyMedia>
          <EmptyTitle className="text-base font-semibold">{item?.label ?? "Trang này"} đang được phát triển</EmptyTitle>
          {item && <EmptyDescription>{item.description}</EmptyDescription>}
          {note && <EmptyDescription className="text-xs">{note}</EmptyDescription>}
        </EmptyHeader>
      </Empty>
    </Card>
  );
}
