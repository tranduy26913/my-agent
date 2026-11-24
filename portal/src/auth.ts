import NextAuth, { customFetch } from "next-auth";
import Zitadel from "next-auth/providers/zitadel";

/**
 * Đăng nhập Zitadel (docs/06 giai đoạn 5, ADR-004). Phiên là JWT mã hoá (JWE) trong cookie httpOnly của portal;
 * access token, refresh token và id token nằm TRONG cookie đó nên trình duyệt không đọc được. Tuyệt đối không
 * trả `session` ra client: route /api/auth/session bị chặn ở src/app/api/auth/[...nextauth]/route.ts.
 *
 * Quyền (vai trò admin...) KHÔNG lấy từ token mà từ GET /api/me của backend (bảng employees), xem lib/me.server.ts.
 */

const ISSUER = (process.env.AUTH_ZITADEL_ISSUER ?? "").replace(/\/$/, "");
const CLIENT_ID = process.env.AUTH_ZITADEL_ID ?? "";
const CLIENT_SECRET = process.env.AUTH_ZITADEL_SECRET ?? "";
const PROJECT_ID = process.env.AUTH_ZITADEL_PROJECT_ID ?? "";
/** Dev khi chưa có route tunnel: gọi Zitadel qua localhost, khai domain ngoài bằng X-Forwarded-Host (xem zitadelFetch). */
const INTERNAL_URL = (process.env.AUTH_ZITADEL_INTERNAL_URL ?? "").replace(/\/$/, "");

/** Làm mới access token khi còn dưới ngần này giây. */
const REFRESH_MARGIN_S = 60;
/** Khớp refresh idle của Zitadel (infra/zitadel/bootstrap.py: 8 giờ). */
const SESSION_MAX_AGE_S = 8 * 60 * 60;

/**
 * fetch tới Zitadel; ở dev có INTERNAL_URL thì chuyển hướng sang địa chỉ nội bộ. Zitadel chọn instance theo domain
 * ngoài, mà fetch của Node (undici) lặng lẽ bỏ header Host tự đặt, nên dùng X-Forwarded-Host/Proto (Zitadel đọc
 * được; đã kiểm bằng discovery).
 */
export const zitadelFetch: typeof fetch = (input, init) => {
  const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
  if (!INTERNAL_URL || !ISSUER || !url.startsWith(ISSUER)) return fetch(input, init);
  const target = INTERNAL_URL + url.slice(ISSUER.length);
  const external = new URL(ISSUER);
  const forward = (h: Headers) => {
    h.set("x-forwarded-host", external.host);
    h.set("x-forwarded-proto", external.protocol.replace(":", ""));
  };
  if (input instanceof Request) {
    const req = new Request(target, input); // giữ method, body, header của Request gốc
    forward(req.headers);
    return fetch(req, init);
  }
  const headers = new Headers(init?.headers);
  forward(headers);
  return fetch(target, { ...init, headers });
};

interface Refreshed {
  accessToken: string;
  refreshToken: string;
  idToken?: string;
  expiresAt: number;
}

/**
 * Zitadel xoay refresh token: dùng một refresh token hai lần thì lần hai bị từ chối. Nhưng một lần tải trang có thể
 * gọi jwt callback nhiều lần (proxy, layout, BFF) với cùng cookie cũ, vì cookie mới chỉ tới được trình duyệt sau
 * cùng. Nên lưu kết quả làm mới theo refresh token CŨ trong vài phút để mọi lần gọi nhận cùng một đáp án.
 * globalThis vì route handler và server component có thể là hai bản module riêng.
 */
const g = globalThis as unknown as { __zitadelRefresh?: Map<string, { at: number; p: Promise<Refreshed> }> };
const refreshCache = (g.__zitadelRefresh ??= new Map());
const REFRESH_CACHE_TTL_MS = 2 * 60 * 1000;

async function requestRefresh(refreshToken: string): Promise<Refreshed> {
  const basic = Buffer.from(`${encodeURIComponent(CLIENT_ID)}:${encodeURIComponent(CLIENT_SECRET)}`).toString("base64");
  const res = await zitadelFetch(`${ISSUER}/oauth/v2/token`, {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded", authorization: `Basic ${basic}` },
    body: new URLSearchParams({ grant_type: "refresh_token", refresh_token: refreshToken }),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Zitadel từ chối làm mới token (${res.status})`);
  const t = (await res.json()) as {
    access_token: string;
    refresh_token?: string;
    id_token?: string;
    expires_in: number;
  };
  return {
    accessToken: t.access_token,
    refreshToken: t.refresh_token ?? refreshToken,
    idToken: t.id_token,
    expiresAt: Math.floor(Date.now() / 1000) + t.expires_in,
  };
}

function refresh(refreshToken: string): Promise<Refreshed> {
  const now = Date.now();
  for (const [k, v] of refreshCache) if (now - v.at > REFRESH_CACHE_TTL_MS) refreshCache.delete(k);
  const hit = refreshCache.get(refreshToken);
  if (hit) return hit.p;
  const p = requestRefresh(refreshToken);
  refreshCache.set(refreshToken, { at: now, p });
  p.catch(() => refreshCache.delete(refreshToken)); // lỗi thì không nhớ, lần sau thử lại
  return p;
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  trustHost: true, // portal chạy sau Cloudflare Tunnel; Host do tunnel đặt
  session: { strategy: "jwt", maxAge: SESSION_MAX_AGE_S },
  pages: { signIn: "/login", error: "/login" },
  providers: [
    Zitadel({
      issuer: ISSUER,
      clientId: CLIENT_ID,
      clientSecret: CLIENT_SECRET,
      checks: ["pkce", "state"], // PKCE là chính; thêm state để chống CSRF ở bước callback
      // `...:aud` đưa project id vào `aud` của access token (FastAPI kiểm); offline_access để có refresh token.
      authorization: {
        params: { scope: `openid profile email offline_access urn:zitadel:iam:org:project:id:${PROJECT_ID}:aud` },
      },
      [customFetch]: zitadelFetch,
    }),
  ],
  callbacks: {
    async jwt({ token, account }) {
      if (account) {
        // Vừa đăng nhập
        return {
          ...token,
          accessToken: account.access_token,
          refreshToken: account.refresh_token,
          idToken: account.id_token,
          expiresAt: account.expires_at,
          error: undefined,
        };
      }
      if (token.error) return token;
      if (token.expiresAt && Date.now() / 1000 < token.expiresAt - REFRESH_MARGIN_S) return token;
      if (!token.refreshToken) return { ...token, error: "RefreshTokenError" as const };
      try {
        const r = await refresh(token.refreshToken);
        return { ...token, ...r, error: undefined };
      } catch {
        return { ...token, error: "RefreshTokenError" as const };
      }
    },
    async session({ session, token }) {
      // Chỉ dùng phía server (me.server.ts, BFF). Không có endpoint nào trả object này cho trình duyệt.
      session.accessToken = token.accessToken;
      session.idToken = token.idToken;
      session.error = token.error;
      return session;
    },
  },
});

/** URL đăng xuất của Zitadel: không gọi thì lần đăng nhập sau vào luôn mà không hỏi mật khẩu. */
export function endSessionUrl(idToken: string | undefined, postLogoutRedirect: string): string {
  const u = new URL(`${ISSUER}/oidc/v1/end_session`);
  if (idToken) u.searchParams.set("id_token_hint", idToken);
  u.searchParams.set("post_logout_redirect_uri", postLogoutRedirect);
  return u.toString();
}
