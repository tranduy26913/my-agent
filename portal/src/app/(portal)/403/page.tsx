import Link from "next/link";
import { ShieldX } from "lucide-react";

export const metadata = { title: "Không có quyền" };

const REASONS: Record<string, string> = {
  admin: "Trang này chỉ dành cho vai trò quản trị viên.",
};

export default async function ForbiddenPage({ searchParams }: { searchParams: Promise<{ need?: string }> }) {
  const { need } = await searchParams;
  const reason = (need && REASONS[need]) ?? "Tài khoản của bạn chưa được cấp quyền xem trang này.";

  return (
    <div className="mx-auto mt-10 flex max-w-md flex-col items-center rounded-2xl bg-p-surface px-6 py-12 text-center">
      <span className="flex size-12 items-center justify-center rounded-full bg-p-err-bg text-p-err">
        <ShieldX className="size-6" />
      </span>
      <h2 className="mt-4 text-base font-semibold">Bạn không có quyền xem trang này</h2>
      <p className="mt-1 text-sm text-p-muted">{reason}</p>
      <p className="mt-1 text-sm text-p-muted">Nếu cần quyền, hãy liên hệ quản trị viên.</p>
      <Link
        href="/"
        className="mt-6 inline-flex h-10 items-center rounded-xl bg-p-secondary px-4 text-sm font-medium transition-colors hover:bg-p-secondary-hover"
      >
        Về trang chủ
      </Link>
    </div>
  );
}
