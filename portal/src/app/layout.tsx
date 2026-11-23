import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Providers } from "@/host/providers";
import "./globals.css";

const inter = Inter({ subsets: ["latin", "vietnamese"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: { default: "Portal · Trợ lý số Sao Việt", template: "%s · Portal" },
  description: "Công cụ cho nhân viên và trang quản trị của trợ lý số nội bộ",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi" className={inter.variable}>
      <body className="font-sans">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
