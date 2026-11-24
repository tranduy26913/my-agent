"use client";

import { useMemo } from "react";
import { OcrPage, createHttpOcrApi, createMockOcrApi } from "@/features/ocr";

/**
 * ADAPTER cho trang OCR: chọn nguồn dữ liệu. Có NEXT_PUBLIC_KB_API_URL thì gọi backend thật (/api/ocr) qua BFF;
 * bỏ trống thì dùng dữ liệu giả. Cùng công tắc với Kho tri thức và Tra cứu.
 */
const USE_BACKEND = !!process.env.NEXT_PUBLIC_KB_API_URL;

export function OcrNextHost() {
  const api = useMemo(() => (USE_BACKEND ? createHttpOcrApi({ baseUrl: "/api/ocr" }) : createMockOcrApi()), []);
  return <OcrPage api={api} />;
}
