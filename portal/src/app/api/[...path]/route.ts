import type { NextRequest } from "next/server";
import { getAskerHeaders, getBackendToken } from "@/lib/backend-token.server";
import { ROLE_ADMIN, hasAnyRole } from "@/lib/me";
import { getMe } from "@/lib/me.server";

/**
 * BFF (ADR-004): trình duyệt gọi `/api/...` cùng origin, file này gắn danh tính rồi chuyển tiếp tới FastAPI.
 * Nhờ vậy backend không cần CORS và token không nằm trong trình duyệt.
 *
 * Chỉ chuyển tiếp những đường dẫn khai ở ROUTES. Mỗi dòng nói rõ ai được gọi và xưng danh kiểu nào. Dòng đứng
 * trước thắng, nên mục cụ thể (kb/ask) phải đặt trước mục chung (kb). Đây là lớp chặn sớm; FastAPI vẫn tự kiểm
 * quyền, không dựa vào lớp này.
 */
const BACKEND_URL = (process.env.BACKEND_URL ?? "http://localhost:8000").replace(/\/$/, "");

interface Rule {
  /** Đường dẫn sau /api/, khớp nguyên văn hoặc làm tiền tố. */
  path: string;
  /** Không khai = mọi người đã đăng nhập. */
  roles?: string[];
  /** Không khai = mọi method. */
  methods?: string[];
  auth: "bearer" | "asker";
}

const ROUTES: Rule[] = [
  { path: "kb/ask", methods: ["POST"], auth: "asker" },
  { path: "kb", roles: [ROLE_ADMIN], auth: "bearer" },
];

type Ctx = { params: Promise<{ path: string[] }> };

function problem(status: number, detail: string) {
  return Response.json({ detail }, { status });
}

async function proxy(req: NextRequest, ctx: Ctx): Promise<Response> {
  const { path } = await ctx.params;
  const joined = path.join("/");
  const rule = ROUTES.find((r) => joined === r.path || joined.startsWith(`${r.path}/`));
  if (!rule) return problem(404, "Không có đường dẫn này");
  if (rule.methods && !rule.methods.includes(req.method)) return problem(405, "Method không được hỗ trợ");

  const me = await getMe();
  if (!hasAnyRole(me, rule.roles)) return problem(403, "Cần vai trò admin");

  // Giữ nguyên dấu ":" trong "documents:reindex" / "documents:delete".
  const target = `${BACKEND_URL}/api/${path.map((s) => encodeURIComponent(s).replace(/%3A/gi, ":")).join("/")}${req.nextUrl.search}`;

  const headers = new Headers();
  const contentType = req.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  if (rule.auth === "bearer") {
    const token = await getBackendToken();
    if (token) headers.set("authorization", `Bearer ${token}`);
  } else {
    for (const [k, v] of Object.entries(getAskerHeaders(me))) headers.set(k, v);
  }

  const hasBody = req.method !== "GET" && req.method !== "HEAD";
  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: req.method,
      headers,
      body: hasBody ? req.body : undefined,
      // Truyền thẳng luồng tải lên, không đọc cả tệp vào bộ nhớ của portal.
      ...(hasBody ? { duplex: "half" } : {}),
      cache: "no-store",
      redirect: "manual",
    } as RequestInit);
  } catch {
    return problem(502, "Không kết nối được backend. Kiểm tra FastAPI đã chạy ở " + BACKEND_URL);
  }

  const out = new Headers();
  const upstreamType = upstream.headers.get("content-type");
  if (upstreamType) out.set("content-type", upstreamType);
  return new Response([204, 205, 304].includes(upstream.status) ? null : upstream.body, {
    status: upstream.status,
    headers: out,
  });
}

export { proxy as GET, proxy as POST, proxy as PUT, proxy as PATCH, proxy as DELETE };
