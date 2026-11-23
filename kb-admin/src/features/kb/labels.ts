import { Globe, Lock, Users, type LucideIcon } from "lucide-react";
import type { DocStatus, Visibility } from "./types";

export const STATUS_META: Record<DocStatus, { label: string; cls: string }> = {
  ready: { label: "Sẵn sàng", cls: "bg-kb-ok-bg text-kb-ok" },
  processing: { label: "Đang xử lý", cls: "bg-kb-neutral-bg text-kb-neutral" },
  error: { label: "Lỗi", cls: "bg-kb-err-bg text-kb-err" },
  quarantined: { label: "Cách ly", cls: "bg-kb-warn-bg text-kb-warn" },
};

export const STATUS_ORDER: DocStatus[] = ["ready", "processing", "error", "quarantined"];

export const VISIBILITY_META: Record<Visibility, { label: string; hint: string; Icon: LucideIcon }> = {
  "cong-khai": { label: "Công khai", hint: "Mọi nhân viên đang làm việc", Icon: Globe },
  "phong-ban": { label: "Theo phòng ban", hint: "Thuộc phòng được chọn, hoặc có vai trò được chọn", Icon: Users },
  "han-che": { label: "Hạn chế", hint: "Phải thuộc phòng được chọn và có vai trò được chọn", Icon: Lock },
};

export const DEPARTMENTS = ["HCNS", "TCKT", "CNTT", "DA", "KD", "BGD"];

export const ROLES: { value: string; label: string }[] = [
  { value: "hr", label: "Nhân sự" },
  { value: "manager", label: "Quản lý" },
  { value: "executive", label: "Ban điều hành" },
];

export const DOC_TYPES: { value: string; label: string }[] = [
  { value: "quy-che", label: "Quy chế" },
  { value: "quy-dinh", label: "Quy định" },
  { value: "quy-trinh", label: "Quy trình" },
  { value: "noi-quy", label: "Nội quy" },
  { value: "chinh-sach", label: "Chính sách" },
  { value: "huong-dan", label: "Hướng dẫn" },
  { value: "thong-bao", label: "Thông báo" },
  { value: "bien-ban-hop", label: "Biên bản họp" },
  { value: "ho-so-du-an", label: "Hồ sơ dự án" },
  { value: "hoi-dap", label: "Hỏi đáp" },
  { value: "chung-tu", label: "Chứng từ" },
];

export function docTypeLabel(value: string | null): string {
  return DOC_TYPES.find((t) => t.value === value)?.label ?? "—";
}
