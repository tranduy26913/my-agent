import { createContext, useContext, type ReactNode } from "react";
import type { KbApi } from "./types";

/**
 * ĐIỂM TÍCH HỢP DUY NHẤT với ứng dụng chủ (Next.js hôm nay, LibreChat sau này).
 * Mô-đun không biết router, không biết cách đăng nhập: chủ truyền vào qua đây.
 *
 * - api:    lấy dữ liệu từ đâu (mock, FastAPI…)
 * - route:  panel nào đang mở. Chủ quyết định lưu ở đâu (URL, state…)
 */
export type KbPanel = "upload" | "detail";

export interface KbRoute {
  panel: KbPanel | null;
  docId: string | null;
  open(panel: KbPanel, docId?: string): void;
  close(): void;
}

export interface KbHost {
  api: KbApi;
  route: KbRoute;
}

const KbHostContext = createContext<KbHost | null>(null);

export function KbHostProvider({ host, children }: { host: KbHost; children: ReactNode }) {
  return <KbHostContext.Provider value={host}>{children}</KbHostContext.Provider>;
}

export function useKbHost(): KbHost {
  const host = useContext(KbHostContext);
  if (!host) throw new Error("Thiếu <KbHostProvider>: bọc mô-đun Kho tri thức trong provider của ứng dụng chủ.");
  return host;
}
