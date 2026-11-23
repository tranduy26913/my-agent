import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // TẠM (docs/08 bước 6): trình duyệt gọi cùng origin `/api/kb/*`, Next chuyển tiếp sang FastAPI.
  // Nhờ vậy KHÔNG phải bật CORS ở backend. Đặt KB_API_PROXY=http://localhost:8000 để dùng.
  // Sau này BFF của portal (ADR-004) thay chỗ này. Không đặt biến thì không có rewrite nào.
  async rewrites() {
    const target = process.env.KB_API_PROXY;
    return target ? [{ source: "/api/kb/:path*", destination: `${target}/api/kb/:path*` }] : [];
  },
};

export default nextConfig;
