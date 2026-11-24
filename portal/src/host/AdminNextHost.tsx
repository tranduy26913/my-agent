"use client";

import { useMemo } from "react";
import { AuditPage, createHttpAuditApi, createMockAuditApi } from "@/features/audit";
import { UsagePage, createHttpUsageApi, createMockUsageApi } from "@/features/usage";

/**
 * ADAPTER cho nhóm trang quản trị đọc dữ liệu từ backend (/api/admin/*): chọn nguồn dữ liệu. Cùng công tắc với Kho tri
 * thức: có NEXT_PUBLIC_KB_API_URL (ví dụ "/api/kb") thì gọi backend thật qua BFF, bỏ trống thì dùng dữ liệu giả.
 */
const USE_BACKEND = !!process.env.NEXT_PUBLIC_KB_API_URL;
const ADMIN_BASE = "/api/admin";

export function AuditNextHost() {
  const api = useMemo(() => (USE_BACKEND ? createHttpAuditApi({ baseUrl: ADMIN_BASE }) : createMockAuditApi()), []);
  return <AuditPage api={api} />;
}

export function UsageNextHost() {
  const api = useMemo(() => (USE_BACKEND ? createHttpUsageApi({ baseUrl: ADMIN_BASE }) : createMockUsageApi()), []);
  return <UsagePage api={api} />;
}
