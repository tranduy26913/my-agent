import { ComingSoon } from "@/shell/ComingSoon";

export const metadata = { title: "Gateway AI" };

/** Khung trống. Sau này: danh sách tài khoản AI (nhà cung cấp, khoá API), hạn mức, định tuyến model. Chưa có backend. */
export default function GatewayRoute() {
  return <ComingSoon href="/admin/gateway" note="Sẽ dùng để quản lý các tài khoản AI (nhà cung cấp, khoá API, hạn mức) tại một chỗ." />;
}
