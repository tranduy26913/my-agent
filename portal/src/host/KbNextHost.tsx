"use client";

import { useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { KbAdminPage, KbHostProvider, createHttpKbApi, createMockKbApi, type KbHost, type KbPanel } from "@/features/kb";

/**
 * ADAPTER cho Next.js. Việc duy nhất: nói cho mô-đun biết
 *  - gọi dữ liệu ở đâu (mock hay FastAPI thật), xác thực thế nào
 *  - panel đang mở được lưu ở đâu (ở đây: query string của URL)
 * Bản LibreChat viết lại đúng file này bằng react-router (xem features/kb/MERGE.md).
 */
export function KbNextHost() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  const api = useMemo(() => {
    const base = process.env.NEXT_PUBLIC_KB_API_URL;
    return base ? createHttpKbApi({ baseUrl: base, credentials: "same-origin" }) : createMockKbApi();
  }, []);

  const rawPanel = params.get("panel");
  const docId = params.get("doc");
  const panel: KbPanel | null = rawPanel === "upload" || (rawPanel === "detail" && docId) ? rawPanel : null;

  const host = useMemo<KbHost>(
    () => ({
      api,
      route: {
        panel,
        docId,
        open(next, id) {
          const q = new URLSearchParams({ panel: next });
          if (id) q.set("doc", id);
          router.push(`${pathname}?${q}`, { scroll: false });
        },
        close() {
          router.push(pathname, { scroll: false });
        },
      },
    }),
    [api, panel, docId, router, pathname],
  );

  return (
    <KbHostProvider host={host}>
      <KbAdminPage />
    </KbHostProvider>
  );
}
