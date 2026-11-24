import { auth } from "@/auth";

/**
 * Cổng chặn sớm: chưa đăng nhập (hoặc không làm mới được token) thì chuyển về /login, riêng /api/* trả 401 JSON.
 * Đây chỉ là kiểm tra "có phiên hay không" cho nhanh (Next: Proxy không phải nơi kiểm quyền); vai trò admin được
 * kiểm ở layout /admin (lib/me.server.ts) và ở FastAPI. Chạy qua `auth` để token hết hạn được làm mới sớm.
 *
 * Danh sách ngoại lệ nằm ở `matcher`: trang đăng nhập, /no-access, callback OIDC, tệp tĩnh.
 */
export const proxy = auth((req) => {
  if (req.auth && !req.auth.error) return;

  const { pathname, search, origin } = req.nextUrl;
  if (pathname.startsWith("/api/")) {
    return Response.json({ detail: "Chưa đăng nhập hoặc phiên đã hết hạn" }, { status: 401 });
  }
  const login = new URL("/login", origin);
  if (req.auth?.error) login.searchParams.set("error", "session");
  login.searchParams.set("callbackUrl", pathname + search);
  return Response.redirect(login);
});

export const config = {
  matcher: ["/((?!login|no-access|api/auth|_next/static|_next/image|favicon.ico|.*\\..*).*)"],
};
