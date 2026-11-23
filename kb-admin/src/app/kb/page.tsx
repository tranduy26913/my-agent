import { Suspense } from "react";
import { AppShell } from "@/host/AppShell";
import { KbNextHost } from "@/host/KbNextHost";

export default function KbPage() {
  return (
    <AppShell title="Kho tri thức">
      {/* useSearchParams (lưu panel đang mở trong URL) cần Suspense */}
      <Suspense>
        <KbNextHost />
      </Suspense>
    </AppShell>
  );
}
