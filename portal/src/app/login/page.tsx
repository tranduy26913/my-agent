import { LogIn } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { loginAction } from "@/lib/auth-actions";

export const metadata = { title: "Đăng nhập" };

const MESSAGES: Record<string, string> = {
  session: "Phiên đăng nhập đã hết hạn. Hãy đăng nhập lại.",
  AccessDenied: "Đăng nhập bị từ chối.",
};

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ callbackUrl?: string; error?: string }>;
}) {
  const { callbackUrl, error } = await searchParams;
  const message = error ? (MESSAGES[error] ?? "Đăng nhập không thành công. Hãy thử lại.") : null;

  return (
    <main className="flex min-h-dvh items-center justify-center bg-background p-4">
      <Card className="w-full max-w-sm py-6">
        <CardHeader>
          <CardTitle className="text-lg">Trợ lý số Công ty A</CardTitle>
          <CardDescription>Đăng nhập bằng tài khoản công ty để dùng công cụ và trang quản trị.</CardDescription>
        </CardHeader>
        {message && (
          <CardContent>
            <p role="alert" className="text-sm text-destructive">
              {message}
            </p>
          </CardContent>
        )}
        <CardFooter>
          <form action={loginAction} className="w-full">
            <input type="hidden" name="callbackUrl" value={callbackUrl ?? "/"} />
            <Button type="submit" className="w-full">
              <LogIn />
              Đăng nhập CTA
            </Button>
          </form>
        </CardFooter>
      </Card>
    </main>
  );
}
