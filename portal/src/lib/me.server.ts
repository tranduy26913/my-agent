import { cookies } from "next/headers";
import { ROLE_ADMIN, type Me } from "./me";

/** Cookie chỉ có tác dụng ở chế độ dev, để thử menu theo vai trò khi chưa có Zitadel. */
export const DEV_ROLE_COOKIE = "portal-dev-role";

// Hai nhân viên có thật trong bảng employees (seed), vì trang Tra cứu lọc quyền xem tài liệu theo email này.
const EMPLOYEE: Me = { name: "Lê Văn Bình", email: "binh.le@saoviet.example", roles: ["nhan-vien"] };
const ADMIN: Me = { name: "Đỗ Quang Huy", email: "huy.do@saoviet.example", roles: [ROLE_ADMIN, "nhan-vien"] };

/**
 * TẠM (docs/07 mục 8, bước 4): trả người dùng giả, đổi vai trò bằng cookie ở chế độ dev.
 * Bản build production luôn trả nhân viên thường, nên không ai tự nâng quyền admin bằng cookie được.
 * Khi Zitadel xong (docs/06, giai đoạn 5): thay thân hàm bằng đọc phiên Auth.js; chỗ gọi không đổi.
 */
export async function getMe(): Promise<Me> {
  if (process.env.NODE_ENV === "production") return EMPLOYEE;
  const role = (await cookies()).get(DEV_ROLE_COOKIE)?.value;
  return role === "employee" ? EMPLOYEE : ADMIN;
}
