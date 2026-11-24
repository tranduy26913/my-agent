import "next-auth";
import "@auth/core/jwt";

/** Token chỉ nằm phía server (xem src/auth.ts): không route nào trả `session` ra trình duyệt. */
declare module "next-auth" {
  interface Session {
    accessToken?: string;
    idToken?: string;
    /** "RefreshTokenError": không làm mới được token, phải đăng nhập lại. */
    error?: "RefreshTokenError";
  }
}

declare module "@auth/core/jwt" {
  interface JWT {
    accessToken?: string;
    refreshToken?: string;
    idToken?: string;
    /** Giây kể từ epoch, như `exp`. */
    expiresAt?: number;
    error?: "RefreshTokenError";
  }
}
