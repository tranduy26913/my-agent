import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { CircleAlert, FileCheck2, Info, TriangleAlert } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";
import type { ExpenseKind, ExtractResult, Finding, OcrApi, Severity } from "../types";

const ACCEPT = ".png,.jpg,.jpeg,.tif,.tiff,.bmp,.pdf,image/png,image/jpeg,image/tiff,image/bmp,application/pdf";
/** Khớp OCR_MAX_MB ở backend (/extract là đồng bộ); backend vẫn là nơi chặn thật. */
const MAX_MB = 20;

const KIND_LABEL: Record<ExpenseKind, string> = {
  phu_cap_luu_tru: "Phụ cấp lưu trú",
  khach_san: "Khách sạn",
  taxi: "Taxi",
  di_lai: "Đi lại",
  tiep_khach: "Tiếp khách",
  khac: "Khác",
};
const SEVERITY_META: Record<Severity, { label: string; Icon: typeof Info; cls: string; row: string }> = {
  error: { label: "Vi phạm", Icon: CircleAlert, cls: "text-destructive", row: "bg-destructive/5" },
  warning: { label: "Cần xem", Icon: TriangleAlert, cls: "text-warning", row: "bg-warning/5" },
  info: { label: "Ghi chú", Icon: Info, cls: "text-muted-foreground", row: "" },
};
const SEVERITY_ORDER: Severity[] = ["error", "warning", "info"];

const money = (n: number) => `${n.toLocaleString("vi-VN")} đ`;
const fmtDate = (d: string) => (/^\d{4}-\d{2}-\d{2}$/.test(d) ? d.split("-").reverse().join("/") : d);
const errText = (e: unknown) => (e instanceof Error ? e.message : "Đã có lỗi xảy ra");

/** Mức nặng nhất của các phát hiện gắn với dòng chi phí `i` (field là "cac_khoan[i]"). */
function worstForLine(findings: Finding[], i: number): Severity | null {
  const mine = findings.filter((f) => f.field === `cac_khoan[${i}]`).map((f) => f.severity);
  return SEVERITY_ORDER.find((s) => mine.includes(s)) ?? null;
}

function Summary({ r }: { r: ExtractResult }) {
  const count = (s: Severity) => r.findings.filter((f) => f.severity === s).length;
  const errors = count("error");
  const warnings = count("warning");
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary" className={r.needsReview ? "bg-warning/10 text-warning" : "bg-success/10 text-success"}>
            {r.needsReview ? "Cần người kiểm tra" : "Chưa phát hiện điểm cần xem"}
          </Badge>
          {errors > 0 ? <Badge variant="destructive">{errors} vi phạm</Badge> : null}
          {warnings > 0 ? (
            <Badge variant="secondary" className="bg-warning/10 text-warning">
              {warnings} điểm cần xem
            </Badge>
          ) : null}
        </div>
        <CardTitle className="mt-1">{r.needsReview ? "Phiếu này cần được xem lại trước khi chuyển duyệt" : "Phiếu qua các bước kiểm tra tự động"}</CardTitle>
        <CardDescription>
          Đây không phải kết luận duyệt chi: hệ thống chỉ chép lại phiếu và đối chiếu với quy định. Người có thẩm quyền vẫn là người quyết định.
        </CardDescription>
      </CardHeader>
    </Card>
  );
}

function FormCard({ r }: { r: ExtractResult }) {
  const f = r.form;
  const fields: [string, string][] = [
    ["Số phiếu", f.formNo || "—"],
    ["Người lập", `${f.fullName || "—"} (${f.employeeCode || "—"})`],
    ["Phòng ban", f.department || "—"],
    ["Nơi công tác", f.place || "—"],
    ["Thời gian công tác", `${fmtDate(f.fromDate)} – ${fmtDate(f.toDate)}`],
    ["Ngày lập phiếu", fmtDate(f.issuedDate)],
  ];
  return (
    <Card>
      <CardHeader>
        <CardTitle>Nội dung đọc được từ phiếu</CardTitle>
        <CardDescription>
          {r.pages} trang, {r.ocrPages} trang phải OCR · {(r.ms / 1000).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} giây · engine {r.engine}, mô hình {r.llmModel}
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        <dl className="grid grid-cols-1 gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
          {fields.map(([k, v]) => (
            <div key={k}>
              <dt className="text-xs text-muted-foreground">{k}</dt>
              <dd className="font-medium">{v}</dd>
            </div>
          ))}
        </dl>
        <div className="overflow-hidden rounded-xl border">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="pl-4">Khoản chi</TableHead>
                <TableHead className="hidden w-24 sm:table-cell">Số lượng</TableHead>
                <TableHead className="hidden w-24 md:table-cell">Hoá đơn</TableHead>
                <TableHead className="w-32 pr-4 text-right">Thành tiền</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {f.lines.map((l, i) => {
                const worst = worstForLine(r.findings, i);
                return (
                  <TableRow key={i} className={cn(worst && SEVERITY_META[worst].row)}>
                    <TableCell className="min-w-40 whitespace-normal pl-4">
                      <p className="text-sm">{l.content}</p>
                      <p className="text-xs text-muted-foreground">
                        {KIND_LABEL[l.kind] ?? l.kind}
                        <span className="sm:hidden"> · {l.quantity}</span>
                        <span className="md:hidden"> · HĐ: {l.invoice === null ? "không rõ" : l.invoice ? "có" : "không"}</span>
                      </p>
                    </TableCell>
                    <TableCell className="hidden sm:table-cell">{l.quantity}</TableCell>
                    <TableCell className="hidden md:table-cell">
                      {l.invoice === null ? <span className="text-muted-foreground">Không rõ</span> : l.invoice ? "Có" : "Không"}
                    </TableCell>
                    <TableCell className="pr-4 text-right tabular-nums">{money(l.amount)}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
          {/* Tổng nằm ngoài bảng: bảng đổi số cột theo cỡ màn hình nên hàng gộp ô (colSpan) sẽ lệch trên điện thoại */}
          <dl className="grid gap-1.5 border-t bg-muted/40 px-4 py-3 text-sm">
            {(
              [
                ["Tổng cộng", f.total],
                ["Đã tạm ứng", f.advance],
                ["Đề nghị thanh toán thêm", f.payMore],
              ] as const
            ).map(([k, v]) => (
              <div key={k} className="flex justify-between gap-4 font-medium">
                <dt>{k}</dt>
                <dd className="tabular-nums">{money(v)}</dd>
              </div>
            ))}
          </dl>
        </div>
      </CardContent>
    </Card>
  );
}

function FindingsCard({ findings }: { findings: Finding[] }) {
  const sorted = [...findings].sort((a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity));
  return (
    <Card>
      <CardHeader>
        <CardTitle>Kết quả kiểm tra</CardTitle>
        <CardDescription>Đối chiếu với văn bản OCR, kiểm tra số học và Quy định công tác phí 08/2025/QĐ-SVT.</CardDescription>
      </CardHeader>
      <CardContent>
        {sorted.length === 0 ? (
          <p className="text-sm text-muted-foreground">Không có phát hiện nào.</p>
        ) : (
          <ul className="grid gap-3">
            {sorted.map((f, i) => {
              const m = SEVERITY_META[f.severity];
              return (
                <li key={i} className="flex gap-3 text-sm">
                  <m.Icon className={cn("mt-0.5 size-4 shrink-0", m.cls)} aria-label={m.label} />
                  <div className="min-w-0">
                    <p>{f.message}</p>
                    <p className="text-xs text-muted-foreground">
                      {[m.label, f.rule, f.overAmount ? `vượt ${money(f.overAmount)}` : null].filter(Boolean).join(" · ")}
                    </p>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * Tab "Phiếu công tác phí": ảnh hoặc PDF của giấy đề nghị thanh toán (BM-CTP-03) -> bảng khoản chi + kết quả kiểm tra.
 * Mô hình chỉ CHÉP chữ ra các trường; kiểm tra số học và quy định là mã tất định ở backend (ADR-005 mục 8).
 * Chỉ kết luận "cần người kiểm tra", không có nút duyệt chi.
 */
export function ExtractPanel({ api }: { api: OcrApi }) {
  const [file, setFile] = useState<File | null>(null);
  const [fileKey, setFileKey] = useState(0);
  const [localError, setLocalError] = useState<string | null>(null);
  const run = useMutation({ mutationFn: (f: File) => api.extract(f) });

  function submit(e?: FormEvent) {
    e?.preventDefault();
    if (!file || run.isPending) return;
    if (file.size > MAX_MB * 1024 * 1024) return setLocalError(`File vượt giới hạn ${MAX_MB} MB.`);
    setLocalError(null);
    run.mutate(file);
    setFile(null);
    setFileKey((k) => k + 1);
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <Card>
        <CardContent>
          <form onSubmit={submit} className="grid gap-4">
            <div className="grid gap-1.5">
              <Label htmlFor="extract-file">Ảnh chụp hoặc PDF của phiếu</Label>
              <Input
                key={fileKey}
                id="extract-file"
                type="file"
                accept={ACCEPT}
                onChange={(e) => {
                  setFile(e.target.files?.[0] ?? null);
                  setLocalError(null);
                }}
                aria-describedby="extract-file-hint"
              />
              <p id="extract-file-hint" className="text-xs text-muted-foreground">
                Giấy đề nghị thanh toán công tác phí (mẫu BM-CTP-03), tối đa {MAX_MB} MB. Việc đọc và kiểm tra thường mất 7 đến 13 giây, lâu hơn khi máy đang bận.
              </p>
            </div>
            <Button type="submit" size="lg" disabled={!file || run.isPending} className="h-10 w-fit px-4">
              {run.isPending ? <Spinner className="motion-reduce:animate-none" /> : <FileCheck2 />}
              Đọc và kiểm tra phiếu
            </Button>
          </form>
        </CardContent>
      </Card>

      {localError || run.isError ? (
        <Alert variant="destructive">
          <TriangleAlert />
          <AlertTitle>Không xử lý được</AlertTitle>
          <AlertDescription>{localError ?? errText(run.error)}</AlertDescription>
        </Alert>
      ) : null}

      {run.isPending ? (
        <Card aria-live="polite" aria-busy>
          <CardContent>
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <Spinner className="motion-reduce:animate-none" />
              Đang đọc phiếu và kiểm tra… vui lòng chờ, đừng đóng trang.
            </p>
          </CardContent>
        </Card>
      ) : null}

      {run.data ? (
        <>
          <Summary r={run.data} />
          <FindingsCard findings={run.data.findings} />
          <FormCard r={run.data} />
        </>
      ) : null}

      <p className="text-center text-xs text-muted-foreground">
        File gốc và kết quả không được lưu lại. Văn bản OCR và phần chép của mô hình có thể sai: hãy đối chiếu với bản gốc.
      </p>
    </div>
  );
}
