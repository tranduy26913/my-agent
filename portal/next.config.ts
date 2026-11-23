import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Đường cũ của kb-admin: giữ một thời gian để link và dấu trang cũ không chết (docs/07 mục 7).
  async redirects() {
    return [{ source: "/kb", destination: "/admin/kb", permanent: false }];
  },
  // Không còn `rewrites` tới FastAPI: `/api/*` đi qua BFF ở src/app/api/[...path]/route.ts (gắn Bearer phía server).
};

export default nextConfig;
