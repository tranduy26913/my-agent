import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Providers } from "@/host/providers";
import { TooltipProvider } from "@/components/ui/tooltip";
import { THEME_INIT_SCRIPT } from "@/shell/ThemeToggle";
import "./globals.css";

// Inter có subset tiếng Việt; Geist (mặc định của shadcn) thì không, dấu sẽ rơi về font hệ thống.
const inter = Inter({ subsets: ["latin", "vietnamese"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: { default: "Portal · Trợ lý số Công ty A", template: "%s · Portal" },
  description: "Công cụ cho nhân viên và trang quản trị của trợ lý số nội bộ",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi" className={inter.variable} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="font-sans">
        <Providers>
          <TooltipProvider>{children}</TooltipProvider>
        </Providers>
      </body>
    </html>
  );
}
