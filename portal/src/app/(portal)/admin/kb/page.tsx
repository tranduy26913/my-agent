import { Suspense } from "react";
import { KbNextHost } from "@/host/KbNextHost";

export const metadata = { title: "Kho tri thức" };

export default function KbPage() {
  return (
    // useSearchParams (lưu panel đang mở trong URL) cần Suspense
    <Suspense>
      <KbNextHost />
    </Suspense>
  );
}
