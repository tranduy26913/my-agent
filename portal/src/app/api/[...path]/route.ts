import type { NextRequest } from "next/server";
import { ROLE_ADMIN, hasAnyRole } from "@/lib/me";
import { resolveSession } from "@/lib/me.server";

/**
 * BFF (ADR-004): trình duyệt gọi `/api/...` cùng origin, file này gắn danh tính rồi chuyển tiếp tới FastAPI.
 * Nhờ vậy backend không cần CORS và token không nằm trong trình duyệt.
 *
 * Chỉ chuyển tiếp những đường dẫn khai ở ROUTES. Mỗi dòng nói rõ ai được gọi. Dòng đứng trước thắng, nên mục cụ
 * thể (kb/ask) phải đặt trước mục chung (kb). Đây là lớp chặn sớm; FastAPI vẫn tự kiểm quyền, không dựa vào lớp này.
 *
 * Xưng danh với FastAPI: gắn access token Zitadel của CHÍNH người đang đăng nhập (Authorization: Bearer). Backend tự
 * kiểm chữ ký và tra quyền theo email trong token, nên portal không thể "nói hộ" quyền của người khác.
 */
const BACKEND_URL = (process.env.BACKEND_URL ?? "http://localhost:8000").replace(/\/$/, "");

interface Rule {
  /** Đường dẫn sau /api/, khớp nguyên văn hoặc làm tiền tố. */
  path: string;
  /** Không khai = mọi người đã đăng nhập. */
  roles?: string[];
  /** Không khai = mọi method. */
  methods?: string[];
}

const ROUTES: Rule[] = [
  { path: "kb/ask", methods: ["POST"] },
  // Thư viện văn bản: mọi nhân viên; backend lọc theo quyền xem của chính người gọi (ADR-001).
  { path: "kb/library", methods: ["GET"] },
  { path: "kb", roles: [ROLE_ADMIN] },
  // Nghỉ phép, danh bạ: mọi nhân viên; backend quyết định xem của ai theo vai trò (ADR-003). Chỉ đọc.
  { path: "hr", methods: ["GET"] },
  // OCR: mọi người đã đăng nhập; backend kiểm tra nhân viên và chỉ cho xem job của chính mình.
  { path: "ocr" },
  // Ghi âm cuộc họp (STT, ADR-006): cùng quy tắc với OCR. Job chỉ chủ xem được.
  { path: "stt" },
  // Tài khoản: tạo, khoá, mở khoá, đặt lại mật khẩu (mọi thao tác ghi vào Nhật ký ở backend).
  { path: "admin/users", methods: ["GET", "POST"], roles: [ROLE_ADMIN] },
  { path: "admin/audit", methods: ["GET"], roles: [ROLE_ADMIN] },
  { path: "admin/usage", methods: ["GET"], roles: [ROLE_ADMIN] },
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

  const r = await resolveSession();
  if (r.status === "login") return problem(401, "Chưa đăng nhập hoặc phiên đã hết hạn");
  if (r.status === "denied") return problem(403, "Tài khoản chưa được cấp quyền dùng portal");
  const { me, accessToken } = r.session;
  if (!hasAnyRole(me, rule.roles)) return problem(403, "Cần vai trò admin");

  // Giữ nguyên dấu ":" trong "documents:reindex" / "documents:delete".
  const target = `${BACKEND_URL}/api/${path.map((s) => encodeURIComponent(s).replace(/%3A/gi, ":")).join("/")}${req.nextUrl.search}`;

  const headers = new Headers();
  const contentType = req.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  headers.set("authorization", `Bearer ${accessToken}`);

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
