import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export default function NotFound() {
  return (
    <main className="flex min-h-dvh items-center justify-center p-6">
      <Card className="max-w-md">
        <CardContent className="px-6 py-6 text-center">
          <p className="text-sm font-medium text-muted-foreground">404</p>
          <h1 className="mt-1 text-lg font-semibold">Không tìm thấy trang</h1>
          <p className="mt-1 text-sm text-muted-foreground">Đường dẫn có thể đã đổi hoặc gõ sai.</p>
          <Button asChild size="lg" className="mt-6 h-10 px-4">
            <Link href="/">Về trang chủ</Link>
          </Button>
        </CardContent>
      </Card>
    </main>
  );
}
