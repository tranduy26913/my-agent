"use client";

import { useMemo } from "react";
import { DirectoryPage, createHttpDirectoryApi } from "@/features/directory";
import { LeavePage, createHttpLeaveApi } from "@/features/leave";

/**
 * ADAPTER cho nhóm trang nhân sự (/api/hr/*): Nghỉ phép và Danh bạ. Không có dữ liệu giả: ai xem được gì do backend quyết
 * định theo vai trò của người đăng nhập (ADR-003), dữ liệu giả sẽ cho thấy một thứ không đúng với quyền thật.
 */
const HR_BASE = "/api/hr";

export function LeaveNextHost() {
  const api = useMemo(() => createHttpLeaveApi({ baseUrl: HR_BASE }), []);
  return <LeavePage api={api} />;
}

export function DirectoryNextHost() {
  const api = useMemo(() => createHttpDirectoryApi({ baseUrl: HR_BASE }), []);
  return <DirectoryPage api={api} />;
}
