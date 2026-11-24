"use client";

import { useMemo } from "react";
import { SttPage, createHttpSttApi, createMockSttApi } from "@/features/stt";

/** ADAPTER cho trang Ghi âm: có NEXT_PUBLIC_KB_API_URL thì gọi backend thật (/api/stt) qua BFF, không thì dùng dữ liệu giả. */
const USE_BACKEND = !!process.env.NEXT_PUBLIC_KB_API_URL;

export function SttNextHost() {
  const api = useMemo(() => (USE_BACKEND ? createHttpSttApi({ baseUrl: "/api/stt" }) : createMockSttApi()), []);
  return <SttPage api={api} />;
}
