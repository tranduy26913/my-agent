import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import type { OcrPageResult } from "../types";

const SOURCE_LABEL = { "text-layer": "Chữ có sẵn trong PDF", ocr: "Nhận dạng ảnh (OCR)" } as const;

function CopyButton({ text, label, size = "sm" }: { text: string; label: string; size?: "sm" | "xs" }) {
  const [done, setDone] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setDone(true);
      setTimeout(() => setDone(false), 1500);
    } catch {
      /* trình duyệt từ chối clipboard: người dùng vẫn chọn và sao chép tay được */
    }
  }
  return (
    <Button type="button" variant="outline" size={size} onClick={copy} disabled={!text} aria-label={label}>
      {done ? <Check /> : <Copy />}
      {done ? "Đã chép" : "Sao chép"}
    </Button>
  );
}

/** Văn bản theo từng trang kèm nguồn (chữ nhúng hay OCR), nút sao chép từng trang và cả tài liệu. */
export function ResultView({ pages, summary }: { pages: OcrPageResult[]; summary: string }) {
  const all = pages.map((p) => p.text).join("\n\n");
  return (
    <Card>
      <CardHeader>
        <CardTitle>Kết quả</CardTitle>
        <CardDescription>{summary}</CardDescription>
        <div className="col-start-2 row-span-2 row-start-1 self-start justify-self-end">
          <CopyButton text={all} label="Sao chép toàn bộ văn bản" />
        </div>
      </CardHeader>
      <CardContent className="grid gap-5">
        {pages.map((p, i) => (
          <section key={p.page} className="grid gap-2" aria-label={`Trang ${p.page}`}>
            {i > 0 ? <Separator className="-mt-2 mb-2" /> : null}
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-sm font-medium">Trang {p.page}</h3>
              <Badge variant={p.source === "ocr" ? "secondary" : "outline"}>{SOURCE_LABEL[p.source]}</Badge>
              <div className="ml-auto">
                <CopyButton text={p.text} label={`Sao chép trang ${p.page}`} size="xs" />
              </div>
            </div>
            {p.text.trim() ? (
              <Textarea readOnly value={p.text} className="min-h-24 font-mono text-sm" aria-label={`Văn bản trang ${p.page}`} />
            ) : (
              <p className="text-sm text-muted-foreground">Không đọc được chữ ở trang này.</p>
            )}
          </section>
        ))}
      </CardContent>
    </Card>
  );
}
