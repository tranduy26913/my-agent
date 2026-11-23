import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-dvh items-center justify-center p-6">
      <div className="max-w-md rounded-2xl bg-p-surface px-6 py-12 text-center">
        <p className="text-sm font-medium text-p-muted">404</p>
        <h1 className="mt-1 text-lg font-semibold">Không tìm thấy trang</h1>
        <p className="mt-1 text-sm text-p-muted">Đường dẫn có thể đã đổi hoặc gõ sai.</p>
        <Link
          href="/"
          className="mt-6 inline-flex h-10 items-center rounded-xl bg-p-primary px-4 text-sm font-medium text-p-on-primary transition-colors hover:bg-p-primary-hover"
        >
          Về trang chủ
        </Link>
      </div>
    </main>
  );
}
