/**
 * Token Bearer mà BFF gắn khi gọi FastAPI. Trình duyệt không bao giờ thấy token này (ADR-004).
 *
 * TẠM (đến khi có Zitadel, docs/06 giai đoạn 4-5): lấy từ biến môi trường `API_DEV_TOKEN` trong `.env.local`,
 * chỉ ở chế độ dev. Production luôn trả null nên BFF gọi backend không kèm token và nhận 401, thay vì
 * để mọi người dùng chung một token admin. Sau này: trả access token Zitadel lấy từ phiên Auth.js.
 */
export async function getBackendToken(): Promise<string | null> {
  if (process.env.NODE_ENV === "production") return null;
  return process.env.API_DEV_TOKEN || null;
}
