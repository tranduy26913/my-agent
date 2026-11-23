import Link from "next/link";
import { ShieldX } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";

export const metadata = { title: "Không có quyền" };

const REASONS: Record<string, string> = {
  admin: "Trang này chỉ dành cho vai trò quản trị viên.",
};

export default async function ForbiddenPage({ searchParams }: { searchParams: Promise<{ need?: string }> }) {
  const { need } = await searchParams;
  const reason = (need && REASONS[need]) ?? "Tài khoản của bạn chưa được cấp quyền xem trang này.";

  return (
    <Card className="mx-auto mt-10 max-w-md py-6">
      <Empty className="border-0">
        <EmptyHeader>
          <EmptyMedia variant="icon" className="size-12 rounded-full bg-destructive/10 text-destructive [&_svg:not([class*='size-'])]:size-6">
            <ShieldX />
          </EmptyMedia>
          <EmptyTitle className="text-base font-semibold">Bạn không có quyền xem trang này</EmptyTitle>
          <EmptyDescription>{reason}</EmptyDescription>
          <EmptyDescription>Nếu cần quyền, hãy liên hệ quản trị viên.</EmptyDescription>
        </EmptyHeader>
        <EmptyContent>
          <Button asChild variant="secondary">
            <Link href="/">Về trang chủ</Link>
          </Button>
        </EmptyContent>
      </Empty>
    </Card>
  );
}
