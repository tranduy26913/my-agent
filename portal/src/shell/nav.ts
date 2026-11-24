import {
  BarChart3,
  BookUser,
  CalendarDays,
  FileText,
  House,
  Library,
  Mic,
  NotebookText,
  ScanText,
  ScrollText,
  Search,
  Users,
  Waypoints,
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
  /** true = ẩn khỏi sidebar và lối tắt trang chủ; trang vẫn còn, vào bằng đường dẫn trực tiếp. Bật lại = xoá dòng hidden. */
  hidden?: boolean;
}

/**
 * NGUỒN DUY NHẤT của điều hướng: sidebar, drawer điện thoại, tiêu đề trang và lối tắt trang chủ đều đọc từ đây
 * (docs/07 mục 2). Thêm trang mới = thêm một dòng ở đây + một file page.tsx.
 */
export const NAV: NavItem[] = [
  { href: "/", label: "Trang chủ", icon: House, group: "main", description: "Lối tắt tới các công cụ.", ready: true },

  { href: "/tools/tra-cuu", label: "Tra cứu", icon: Search, group: "tools", description: "Hỏi đáp về quy chế, có trích dẫn nguồn.", ready: true },
  { href: "/tools/van-ban", label: "Văn bản", icon: FileText, group: "tools", description: "Duyệt các văn bản bạn được xem.", ready: true, hidden: true },
  { href: "/tools/nghi-phep", label: "Nghỉ phép", icon: CalendarDays, group: "tools", description: "Số ngày phép còn lại và đơn nghỉ.", ready: true, hidden: true },
  { href: "/tools/danh-ba", label: "Danh bạ", icon: BookUser, group: "tools", description: "Tìm đồng nghiệp theo tên, phòng ban.", ready: true, hidden: true },
  { href: "/tools/ocr", label: "OCR", icon: ScanText, group: "tools", description: "Lấy văn bản từ ảnh hoặc PDF.", ready: true },

  { href: "/tools/ghi-am", label: "Ghi âm", icon: Mic, group: "tools", description: "Chuyển ghi âm cuộc họp thành văn bản.", ready: true },
  { href: "/tools/prompt", label: "Thư viện prompt", icon: NotebookText, group: "tools", description: "Prompt mẫu cho việc hằng ngày, ai cũng thêm được.", ready: true },

  { href: "/admin/kb", label: "Kho tri thức", icon: Library, group: "admin", roles: ["admin"], description: "Nạp, kiểm tra và phân quyền tài liệu.", ready: true },
  { href: "/admin/users", label: "Tài khoản", icon: Users, group: "admin", roles: ["admin"], description: "Tạo, khoá, đặt lại mật khẩu.", ready: true },
  { href: "/admin/gateway", label: "Gateway AI", icon: Waypoints, group: "admin", roles: ["admin"], description: "Quản lý tài khoản AI, khoá API và hạn mức qua một cổng chung.", ready: false },
  { href: "/admin/audit", label: "Nhật ký", icon: ScrollText, group: "admin", roles: ["admin"], description: "Ai đã làm gì, lúc nào.", ready: true },
  { href: "/admin/usage", label: "Chi phí", icon: BarChart3, group: "admin", roles: ["admin"], description: "Lượt gọi và chi phí theo người, theo model.", ready: true },
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
