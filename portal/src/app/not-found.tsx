import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";

export default function NotFound() {
  return (
    <main className="flex min-h-dvh items-center justify-center p-6">
      <Card className="max-w-md py-6">
        <Empty className="border-0">
          <EmptyHeader>
            <p className="text-sm font-medium text-muted-foreground">404</p>
            <EmptyTitle className="text-lg font-semibold">Không tìm thấy trang</EmptyTitle>
            <EmptyDescription>Đường dẫn có thể đã đổi hoặc gõ sai.</EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <Button asChild>
              <Link href="/">Về trang chủ</Link>
            </Button>
          </EmptyContent>
        </Empty>
      </Card>
    </main>
  );
}
