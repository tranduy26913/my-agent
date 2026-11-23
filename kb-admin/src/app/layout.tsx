import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Providers } from "@/host/providers";
import "./globals.css";

const inter = Inter({ subsets: ["latin", "vietnamese"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Kho tri thức · Quản trị",
  description: "Nạp và quản lý tài liệu cho trợ lý số nội bộ",
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
