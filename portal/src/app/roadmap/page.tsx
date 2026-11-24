import { RoadmapPage } from "@/features/roadmap";

// Trang công khai: nằm ngoài nhóm (portal) nên không qua kiểm tra đăng nhập; src/proxy.ts cũng loại /roadmap khỏi cổng chặn.
export const metadata = {
  title: "Lộ trình đưa AI vào doanh nghiệp",
  description: "Kế hoạch triển khai AI theo giai đoạn: quản trị, con người, công cụ, cổng duyệt, chỉ số và rủi ro.",
};

export default function Page() {
  return <RoadmapPage />;
}
