import { ShieldX } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { logoutAction } from "@/lib/auth-actions";

export const metadata = { title: "Chưa được cấp quyền" };

/** Người đã đăng nhập Zitadel nhưng backend không cho vào. Nằm ngoài khung (portal) để không tự gọi lại getMe(). */
const REASONS: Record<string, { title: string; text: string }> = {
  directory: {
    title: "Tài khoản chưa có trong danh bạ nhân sự",
    text: "Bạn đã đăng nhập được, nhưng email của bạn chưa có trong danh bạ nhân sự SVT nên chưa được cấp quyền. Hãy liên hệ phòng Hành chính nhân sự.",
  },
  inactive: {
    title: "Tài khoản nhân sự không còn hoạt động",
    text: "Hồ sơ nhân sự của bạn đang ở trạng thái đã nghỉ việc nên không thể dùng portal.",
  },
  token: {
    title: "Máy chủ từ chối phiên đăng nhập",
    text: "Phiên đăng nhập của bạn không được backend chấp nhận. Hãy đăng xuất rồi đăng nhập lại; nếu vẫn lỗi, báo quản trị viên.",
  },
  backend: {
    title: "Không kết nối được máy chủ",
    text: "Portal chưa gọi được backend để xác định quyền của bạn. Hãy thử lại sau ít phút.",
  },
};

export default async function NoAccessPage({ searchParams }: { searchParams: Promise<{ reason?: string }> }) {
  const { reason } = await searchParams;
  const r = REASONS[reason ?? ""] ?? REASONS.token;

  return (
    <main className="flex min-h-dvh items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md py-6">
        <Empty className="border-0">
          <EmptyHeader>
            <EmptyMedia variant="icon" className="size-12 rounded-full bg-destructive/10 text-destructive [&_svg:not([class*='size-'])]:size-6">
              <ShieldX />
            </EmptyMedia>
            <EmptyTitle className="text-base font-semibold">{r.title}</EmptyTitle>
            <EmptyDescription>{r.text}</EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <form action={logoutAction}>
              <Button type="submit" variant="secondary">
                Đăng xuất
              </Button>
            </form>
          </EmptyContent>
        </Empty>
      </Card>
    </main>
  );
}
