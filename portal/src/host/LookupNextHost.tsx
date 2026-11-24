"use client";

import { useMemo } from "react";
import { LookupPage, createHttpLookupApi, createMockLookupApi } from "@/features/lookup";

/**
 * ADAPTER cho trang Tra cứu: chọn nguồn dữ liệu. Có NEXT_PUBLIC_KB_API_URL (ví dụ "/api/kb") thì gọi backend thật
 * qua BFF; bỏ trống thì dùng dữ liệu giả. Cùng một biến với trang Kho tri thức để bật/tắt backend thật một lần.
 */
export function LookupNextHost() {
  const api = useMemo(() => {
    const base = process.env.NEXT_PUBLIC_KB_API_URL;
    return base ? createHttpLookupApi({ baseUrl: base }) : createMockLookupApi();
  }, []);
  return <LookupPage api={api} />;
}
