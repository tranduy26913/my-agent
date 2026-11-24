import type { NextRequest } from "next/server";
import { handlers } from "@/auth";

/**
 * Chỉ mở đúng bước callback của OIDC. Các route khác của Auth.js (/session, /csrf, /signin, /signout...) bị chặn:
 * - /session trả object chứa access token ra trình duyệt, trái nguyên tắc "trình duyệt không cầm token" (ADR-004);
 * - đăng nhập/đăng xuất đi bằng server action (src/lib/auth-actions.ts), không cần các route đó.
 */
const ALLOWED = /^\/api\/auth\/callback\/zitadel$/;

function guard(handler: (req: NextRequest) => Promise<Response>) {
  return (req: NextRequest) =>
    ALLOWED.test(req.nextUrl.pathname)
      ? handler(req)
      : Response.json({ detail: "Không có đường dẫn này" }, { status: 404 });
}

export const GET = guard(handlers.GET);
export const POST = guard(handlers.POST);
