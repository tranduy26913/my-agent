import {
  BarChart3,
  BookUser,
  CalendarDays,
  FileText,
  House,
  Library,
  ScanText,
  ScrollText,
  Search,
  Users,
  type LucideIcon,
} from "lucide-react";

export type NavGroup = "main" | "tools" | "admin";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  group: NavGroup;
  /** Không khai = mọi người đều thấy. Chỉ để ẩn menu cho gọn; quyền thật do layout và API kiểm. */
  roles?: string[];
  /** Một câu mô tả, hiện ở lối tắt trang chủ. */
  description: string;
  /** false = trang tạm "Đang phát triển". */
  ready: boolean;
}

/**
 * NGUỒN DUY NHẤT của điều hướng: sidebar, drawer điện thoại, tiêu đề trang và lối tắt trang chủ đều đọc từ đây
 * (docs/07 mục 2). Thêm trang mới = thêm một dòng ở đây + một file page.tsx.
 */
export const NAV: NavItem[] = [
  { href: "/", label: "Trang chủ", icon: House, group: "main", description: "Lối tắt tới các công cụ.", ready: true },

  { href: "/tools/tra-cuu", label: "Tra cứu", icon: Search, group: "tools", description: "Hỏi đáp về quy chế, có trích dẫn nguồn.", ready: true },
  { href: "/tools/van-ban", label: "Văn bản", icon: FileText, group: "tools", description: "Duyệt các văn bản bạn được xem.", ready: false },
  { href: "/tools/nghi-phep", label: "Nghỉ phép", icon: CalendarDays, group: "tools", description: "Số ngày phép còn lại và đơn nghỉ.", ready: false },
  { href: "/tools/danh-ba", label: "Danh bạ", icon: BookUser, group: "tools", description: "Tìm đồng nghiệp theo tên, phòng ban.", ready: false },
  { href: "/tools/ocr", label: "OCR", icon: ScanText, group: "tools", description: "Lấy văn bản từ ảnh hoặc PDF.", ready: false },

  { href: "/admin/kb", label: "Kho tri thức", icon: Library, group: "admin", roles: ["admin"], description: "Nạp, kiểm tra và phân quyền tài liệu.", ready: true },
  { href: "/admin/users", label: "Tài khoản", icon: Users, group: "admin", roles: ["admin"], description: "Tạo, khoá, đặt lại mật khẩu.", ready: false },
  { href: "/admin/audit", label: "Nhật ký", icon: ScrollText, group: "admin", roles: ["admin"], description: "Ai đã làm gì, lúc nào.", ready: false },
  { href: "/admin/usage", label: "Chi phí", icon: BarChart3, group: "admin", roles: ["admin"], description: "Lượt gọi và chi phí theo người, theo model.", ready: false },
];

export const GROUP_LABEL: Record<NavGroup, string | null> = {
  main: null,
  tools: "Công cụ",
  admin: "Quản trị",
};

export const CHAT_URL = process.env.NEXT_PUBLIC_CHAT_URL ?? "http://localhost:3080";

/** Trang không có trong menu nhưng vẫn cần tiêu đề ở header. */
export const EXTRA_TITLES: Record<string, string> = { "/403": "Không có quyền" };

export function findNavItem(pathname: string): NavItem | undefined {
  return NAV.find((n) => (n.href === "/" ? pathname === "/" : pathname === n.href || pathname.startsWith(`${n.href}/`)));
}
