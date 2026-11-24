"use client";

import { useMemo } from "react";
import { LibraryPage, createHttpLibraryApi } from "@/features/library";

/** ADAPTER cho trang Văn bản. Không có dữ liệu giả: danh sách phụ thuộc quyền xem của chính người đăng nhập (docs/07 mục 9). */
export function LibraryNextHost() {
  const api = useMemo(() => createHttpLibraryApi({ baseUrl: "/api/kb" }), []);
  return <LibraryPage api={api} />;
}
