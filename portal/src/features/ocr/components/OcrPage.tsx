import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ScanText, TriangleAlert } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Spinner } from "@/components/ui/spinner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { OcrApi, OcrResult } from "../types";
import { ExtractPanel } from "./ExtractPanel";
import { JobList } from "./JobList";
import { ResultView } from "./ResultView";

const ACCEPT = ".png,.jpg,.jpeg,.tif,.tiff,.bmp,.pdf,image/png,image/jpeg,image/tiff,image/bmp,application/pdf";
/** Khớp OCR_MAX_MB (ảnh, đồng bộ) và OCR_JOB_MAX_MB (PDF, job) ở backend; backend vẫn là nơi chặn thật. */
const MAX_IMAGE_MB = 20;
const MAX_PDF_MB = 50;
const PAGES_PATTERN = /^[\d,\-\s]*$/;

const isPdf = (f: File) => f.type === "application/pdf" || /\.pdf$/i.test(f.name);
const fmtSeconds = (ms: number) => `${(ms / 1000).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} giây`;
const errText = (e: unknown) => (e instanceof Error ? e.message : "Đã có lỗi xảy ra");

const jobsKey = ["ocr", "jobs"] as const;
const jobKey = (id: string) => ["ocr", "job", id] as const;

/**
 * Tab "Đọc chữ": lấy chữ từ ảnh hoặc PDF. Ảnh (một trang) đọc đồng bộ và không lưu; PDF chạy job nền, có tiến độ và lịch sử
 * 7 ngày. KHÔNG nạp vào kho tri thức (đó là việc của /admin/kb). KHÔNG gồm sidebar / header: đó là khung của portal.
 */
function TextPanel({ api }: { api: OcrApi }) {
  const qc = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [fileKey, setFileKey] = useState(0); // đổi key để xoá ô chọn file sau khi gửi
  const [pages, setPages] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const [syncResult, setSyncResult] = useState<OcrResult | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const sync = useMutation({
    mutationFn: (f: File) => api.recognize(f, { pages }),
    onSuccess: (r) => setSyncResult(r),
  });
  const create = useMutation({
    mutationFn: (f: File) => api.createJob(f, { pages }),
    onSuccess: (job) => {
      setSelectedId(job.id);
      void qc.invalidateQueries({ queryKey: jobsKey });
    },
  });
  const remove = useMutation({
    mutationFn: (id: string) => api.deleteJob(id),
    onSuccess: (_, id) => {
      if (selectedId === id) setSelectedId(null);
      void qc.invalidateQueries({ queryKey: jobsKey });
    },
  });

  const jobs = useQuery({
    queryKey: jobsKey,
    queryFn: () => api.listJobs(),
    refetchInterval: (q) => (q.state.data?.some((j) => j.status === "queued" || j.status === "running") ? 2000 : false),
  });
  const detail = useQuery({
    queryKey: jobKey(selectedId ?? ""),
    queryFn: () => api.getJob(selectedId!),
    enabled: selectedId !== null,
    refetchInterval: (q) => (q.state.data && (q.state.data.status === "queued" || q.state.data.status === "running") ? 1500 : false),
  });

  const busy = sync.isPending || create.isPending;
  const submitError = sync.isError ? errText(sync.error) : create.isError ? errText(create.error) : null;

  function onFile(f: File | null) {
    setFile(f);
    setLocalError(null);
  }

  function submit(e?: FormEvent) {
    e?.preventDefault();
    if (!file || busy) return;
    if (!PAGES_PATTERN.test(pages)) return setLocalError("Trang cần đọc chỉ gồm số, dấu phẩy và dấu gạch, ví dụ 1,3-5.");
    const pdf = isPdf(file);
    const limit = pdf ? MAX_PDF_MB : MAX_IMAGE_MB;
    if (file.size > limit * 1024 * 1024) return setLocalError(`File vượt giới hạn ${limit} MB.`);
    setLocalError(null);
    setSyncResult(null);
    setSelectedId(null);
    sync.reset();
    create.reset();
    if (pdf) create.mutate(file);
    else sync.mutate(file);
    setFile(null);
    setFileKey((k) => k + 1);
  }

  const job = detail.data;
  const running = job && (job.status === "queued" || job.status === "running");
  const percent = job && job.pagesTotal > 0 ? Math.round((job.pagesDone / job.pagesTotal) * 100) : 0;

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <Card>
        <CardContent>
          <form onSubmit={submit} className="grid gap-4">
            <div className="grid gap-1.5">
              <Label htmlFor="ocr-file">Ảnh hoặc PDF</Label>
              <Input
                key={fileKey}
                id="ocr-file"
                type="file"
                accept={ACCEPT}
                onChange={(e) => onFile(e.target.files?.[0] ?? null)}
                aria-describedby="ocr-file-hint"
              />
              <p id="ocr-file-hint" className="text-xs text-muted-foreground">
                PNG, JPEG, TIFF, BMP (đọc ngay, tối đa {MAX_IMAGE_MB} MB) hoặc PDF (chạy nền, tối đa {MAX_PDF_MB} MB).
              </p>
            </div>
            <div className="flex flex-wrap items-end gap-3">
              <div className="grid gap-1.5">
                <Label htmlFor="ocr-pages" className="text-xs font-normal text-muted-foreground">
                  Chỉ đọc các trang (để trống là tất cả)
                </Label>
                <Input
                  id="ocr-pages"
                  value={pages}
                  onChange={(e) => setPages(e.target.value)}
                  placeholder="Ví dụ 1,3-5"
                  inputMode="numeric"
                  className="h-9 w-44"
                />
              </div>
              <Button type="submit" size="lg" disabled={!file || busy} className="ml-auto h-10 px-4">
                {busy ? <Spinner className="motion-reduce:animate-none" /> : <ScanText />}
                Đọc chữ
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {localError || submitError ? (
        <Alert variant="destructive">
          <TriangleAlert />
          <AlertTitle>Không xử lý được</AlertTitle>
          <AlertDescription>{localError ?? submitError}</AlertDescription>
        </Alert>
      ) : null}

      {sync.isPending ? (
        <Card aria-live="polite" aria-busy>
          <CardContent>
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <Spinner className="motion-reduce:animate-none" />
              Đang đọc ảnh… thường mất vài giây.
            </p>
          </CardContent>
        </Card>
      ) : null}

      {create.isPending ? (
        <Card aria-live="polite" aria-busy>
          <CardContent>
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <Spinner className="motion-reduce:animate-none" />
              Đang tải PDF lên…
            </p>
          </CardContent>
        </Card>
      ) : null}

      {syncResult ? (
        <ResultView
          pages={syncResult.pages}
          summary={`${fmtSeconds(syncResult.ms)} · engine ${syncResult.engine} · không lưu lại`}
        />
      ) : null}

      {selectedId && detail.isError ? (
        <Alert variant="destructive">
          <TriangleAlert />
          <AlertTitle>Không mở được job</AlertTitle>
          <AlertDescription>{errText(detail.error)}</AlertDescription>
        </Alert>
      ) : null}

      {running ? (
        <Card aria-live="polite" aria-busy>
          <CardContent className="grid gap-3">
            <p className="text-sm font-medium">
              {job.status === "queued" ? "Đang chờ tới lượt…" : `Đang đọc trang ${Math.min(job.pagesDone + 1, job.pagesTotal)}/${job.pagesTotal}…`}
            </p>
            <Progress value={percent} aria-label="Tiến độ đọc PDF" />
            <p className="text-xs text-muted-foreground">Bạn có thể rời trang này: job vẫn chạy và nằm trong danh sách bên dưới.</p>
          </CardContent>
        </Card>
      ) : null}

      {job?.status === "failed" ? (
        <Alert variant="destructive">
          <TriangleAlert />
          <AlertTitle>Job thất bại</AlertTitle>
          <AlertDescription>{job.error ?? "Lỗi không rõ"}. Hãy gửi lại file.</AlertDescription>
        </Alert>
      ) : null}

      {job?.status === "done" && job.pages ? (
        <ResultView
          pages={job.pages}
          summary={`${job.pagesTotal} trang, ${job.ocrPages ?? 0} trang phải OCR · engine ${job.engine} · lưu tới hết hạn`}
        />
      ) : null}

      {jobs.data && jobs.data.length > 0 ? (
        <JobList
          jobs={jobs.data}
          selectedId={selectedId}
          deletingId={remove.isPending ? (remove.variables ?? null) : null}
          onOpen={(id) => {
            setSyncResult(null);
            setSelectedId(id);
          }}
          onDelete={(id) => remove.mutate(id)}
        />
      ) : null}

      {remove.isError ? (
        <Alert variant="destructive">
          <TriangleAlert />
          <AlertTitle>Không xoá được job</AlertTitle>
          <AlertDescription>{errText(remove.error)}</AlertDescription>
        </Alert>
      ) : null}

      <p className="text-center text-xs text-muted-foreground">
        File gốc và tên file không được lưu. Văn bản OCR có thể sai: hãy đối chiếu với bản gốc trước khi dùng cho việc quan trọng.
      </p>
    </div>
  );
}

/**
 * Trang OCR gồm hai tab: "Đọc chữ" (lấy văn bản từ ảnh/PDF) và "Phiếu công tác phí" (trích xuất và kiểm tra phiếu).
 * Hai tab giữ nguyên nội dung khi chuyển qua lại (forceMount + ẩn), để đang chạy job hay vừa có kết quả không bị mất.
 */
export function OcrPage({ api }: { api: OcrApi }) {
  return (
    <Tabs defaultValue="text" className="mx-auto max-w-3xl gap-4">
      <TabsList aria-label="Chế độ">
        <TabsTrigger value="text">Đọc chữ</TabsTrigger>
        <TabsTrigger value="extract">Phiếu công tác phí</TabsTrigger>
      </TabsList>
      <TabsContent value="text" forceMount className="data-[state=inactive]:hidden">
        <TextPanel api={api} />
      </TabsContent>
      <TabsContent value="extract" forceMount className="data-[state=inactive]:hidden">
        <ExtractPanel api={api} />
      </TabsContent>
    </Tabs>
  );
}
