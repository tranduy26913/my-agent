import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Cho phép chạy thêm một instance dev song song (vd kiểm giao diện ở cổng khác) mà không tranh khoá thư mục .next.
  distDir: process.env.NEXT_DIST_DIR || ".next",
  // Proxy (src/proxy.ts) khớp cả /api/*: mặc định Next đệm tối đa 10 MB thân request nên upload ghi âm sẽ bị cắt (ADR-006).
  // Khớp STT_MAX_MB ở backend.
  experimental: { proxyClientMaxBodySize: "300mb" },
  // Đường cũ của kb-admin: giữ một thời gian để link và dấu trang cũ không chết (docs/07 mục 7).
  async redirects() {
    return [{ source: "/kb", destination: "/admin/kb", permanent: false }];
  },
  // Không còn `rewrites` tới FastAPI: `/api/*` đi qua BFF ở src/app/api/[...path]/route.ts (gắn Bearer phía server).
};

export default nextConfig;
