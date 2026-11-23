import Link from "next/link";
import { ShieldX } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export const metadata = { title: "Không có quyền" };

const REASONS: Record<string, string> = {
  admin: "Trang này chỉ dành cho vai trò quản trị viên.",
};

export default async function ForbiddenPage({ searchParams }: { searchParams: Promise<{ need?: string }> }) {
  const { need } = await searchParams;
  const reason = (need && REASONS[need]) ?? "Tài khoản của bạn chưa được cấp quyền xem trang này.";

  return (
    <Card className="mx-auto mt-10 max-w-md">
      <CardContent className="flex flex-col items-center px-6 py-6 text-center">
        <span className="flex size-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
          <ShieldX className="size-6" />
        </span>
        <h2 className="mt-4 text-base font-semibold">Bạn không có quyền xem trang này</h2>
        <p className="mt-1 text-sm text-muted-foreground">{reason}</p>
        <p className="mt-1 text-sm text-muted-foreground">Nếu cần quyền, hãy liên hệ quản trị viên.</p>
        <Button asChild variant="secondary" size="lg" className="mt-6 h-10 px-4">
          <Link href="/">Về trang chủ</Link>
        </Button>
      </CardContent>
    </Card>
  );
}
