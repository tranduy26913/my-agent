import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  globalIgnores([".next/**", ".next-*/**", "out/**", "build/**", "next-env.d.ts"]),

  // HÀNG RÀO GIỮ LOGIC GIAO DIỆN TÁCH KHỎI ROUTER: src/features/* không import next/*, để dễ test và không dính vào router.
  // Phần dính tới Next (router, provider, font) chỉ nằm ở src/host và src/app.
  // Được dùng bộ component dùng chung (@/components/ui/* của shadcn) và @/lib/utils; không import gì khác ngoài mô-đun.
  {
    files: ["src/features/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            { group: ["next", "next/*"], message: "Mô-đun giao diện không import Next.js. Đưa phần này sang src/host (adapter)." },
            // Không dùng "@/*" kèm phủ định: gitignore không cho "bỏ chặn" con khi thư mục cha đã bị chặn.
            {
              group: ["@/app/**", "@/shell/**", "@/host/**", "@/hooks/**", "@/features/**", "@/lib/me", "@/lib/me.*"],
              message: "Mô-đun chỉ được import @/components/ui/* và @/lib/utils từ ngoài mô-đun. Phần khác của portal thì đưa vào host (adapter).",
            },
            { group: ["server-only", "client-only"], message: "Mô-đun giao diện không dùng cơ chế riêng của Next." },
          ],
        },
      ],
    },
  },
]);

export default eslintConfig;
