import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts"]),

  // HÀNG RÀO GIỮ MÔ-ĐUN DỄ GỘP: src/features/kb không được biết gì về Next.js hay phần còn lại của app.
  // Phần dính tới Next (router, provider, font) chỉ được nằm ở src/host và src/app.
  {
    files: ["src/features/kb/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            { group: ["next", "next/*"], message: "Mô-đun kb phải chạy được ngoài Next.js. Đưa phần này sang src/host (adapter)." },
            { group: ["@/*"], message: "Chỉ dùng đường dẫn tương đối trong mô-đun kb. Không import ngược ra ngoài mô-đun." },
            { group: ["../../*", "../../../*"], message: "Không import ra ngoài thư mục mô-đun kb." },
            { group: ["server-only", "client-only"], message: "Mô-đun kb không dùng cơ chế riêng của Next." },
          ],
        },
      ],
    },
  },
]);

export default eslintConfig;
