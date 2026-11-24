import "server-only";
import { cache } from "react";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { ROLE_ADMIN, type Me } from "./me";

/**
 * Người dùng đang đăng nhập (docs/06 giai đoạn 5). Danh tính lấy từ phiên Auth.js (token Zitadel); họ tên, vai trò
 * và phòng ban lấy từ GET /api/me của backend, tức bảng employees, KHÔNG đọc từ token (ADR-004 mục 3).
 */

const BACKEND_URL = (process.env.BACKEND_URL ?? "http://localhost:8000").replace(/\/$/, "");

/** Cookie chỉ có tác dụng khi PORTAL_DEV_AUTH=1, để thử menu theo vai trò. */
export const DEV_ROLE_COOKIE = "portal-dev-role";

/**
 * TẠM, chỉ để làm giao diện khi chưa đăng nhập được (vd chưa có route tunnel tới Zitadel): PORTAL_DEV_AUTH=1 dùng
 * người dùng giả, đổi vai trò bằng cookie. Production luôn bỏ qua cờ này. Gỡ ở giai đoạn 6 (docs/06).
 */
export const DEV_AUTH = process.env.NODE_ENV !== "production" && process.env.PORTAL_DEV_AUTH === "1";

// Hai nhân viên có thật trong bảng employees (seed), vì trang Tra cứu lọc quyền xem tài liệu theo email này.
const DEV_EMPLOYEE: Me = { name: "Lê Văn Bình", email: "binh.le@saoviet.example", roles: ["employee"] };
const DEV_ADMIN: Me = { name: "Đỗ Quang Huy", email: "huy.do@saoviet.example", roles: [ROLE_ADMIN, "employee"] };

/** Vì sao một người đã đăng nhập Zitadel vẫn không vào được portal (trang /no-access). */
export type DenyReason = "directory" | "inactive" | "token" | "backend";

export interface PortalSession {
  me: Me;
  /** Access token Zitadel để BFF gắn vào request tới FastAPI. null khi DEV_AUTH. */
  accessToken: string | null;
}

export type SessionResult =
  | { status: "ok"; session: PortalSession }
  | { status: "login" }
  | { status: "denied"; reason: DenyReason };

async function fetchMe(accessToken: string): Promise<SessionResult> {
  let res: Response;
  try {
    res = await fetch(`${BACKEND_URL}/api/me`, {
      headers: { authorization: `Bearer ${accessToken}` },
      cache: "no-store",
    });
  } catch {
    return { status: "denied", reason: "backend" };
  }
  if (res.status === 401) return { status: "denied", reason: "token" };
  if (res.status === 403) {
    const detail = ((await res.json().catch(() => ({}))) as { detail?: string }).detail ?? "";
    return { status: "denied", reason: detail.includes("danh bạ") ? "directory" : "inactive" };
  }
  if (!res.ok) return { status: "denied", reason: "backend" };
  const body = (await res.json()) as { email: string; name: string; roles: string[] };
  return { status: "ok", session: { me: { name: body.name, email: body.email, roles: body.roles }, accessToken } };
}

/** Trạng thái đăng nhập của request hiện tại. Không redirect: dùng cho route handler (BFF) cần trả JSON. */
export const resolveSession = cache(async (): Promise<SessionResult> => {
  if (DEV_AUTH) {
    const role = (await cookies()).get(DEV_ROLE_COOKIE)?.value;
    return { status: "ok", session: { me: role === "employee" ? DEV_EMPLOYEE : DEV_ADMIN, accessToken: null } };
  }
  const s = await auth();
  if (!s || s.error || !s.accessToken) return { status: "login" };
  return fetchMe(s.accessToken);
});

/** Dùng trong server component và layout: chưa đăng nhập thì chuyển trang, không để lọt. */
export async function getPortalSession(): Promise<PortalSession> {
  const r = await resolveSession();
  if (r.status === "login") redirect("/login");
  if (r.status === "denied") redirect(`/no-access?reason=${r.reason}`);
  return r.session;
}

export async function getMe(): Promise<Me> {
  return (await getPortalSession()).me;
}
