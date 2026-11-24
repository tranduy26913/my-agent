import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Copy, Download, Eye, Mic, Trash2, TriangleAlert } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogMedia,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Item, ItemActions, ItemContent, ItemDescription, ItemGroup, ItemTitle } from "@/components/ui/item";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Spinner } from "@/components/ui/spinner";
import { fmtClock, toPlainText, toSrt } from "../format";
import type { JobStatus, Segment, SttApi, SttJob } from "../types";

/** Khớp STT_MAX_MB ở backend; backend vẫn là nơi chặn thật. */
const MAX_MB = 300;
const ACCEPT = "audio/*,video/mp4,video/webm,.mp3,.wav,.m4a,.aac,.ogg,.opus,.flac,.wma,.mp4,.mkv,.webm,.mov";

const errText = (e: unknown) => (e instanceof Error ? e.message : "Đã có lỗi xảy ra");
const isActive = (s: JobStatus) => s === "queued" || s === "running";
const fmtDateTime = (iso: string) =>
  new Date(iso).toLocaleString("vi-VN", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });

const STATUS: Record<JobStatus, { label: string; variant: "secondary" | "outline" | "destructive" | "default" }> = {
  queued: { label: "Đang chờ", variant: "outline" },
  running: { label: "Đang chép", variant: "secondary" },
  done: { label: "Xong", variant: "default" },
  failed: { label: "Lỗi", variant: "destructive" },
};

const jobsKey = ["stt", "jobs"] as const;
const jobKey = (id: string) => ["stt", "job", id] as const;
const enginesKey = ["stt", "engines"] as const;

function save(name: string, text: string, type: string) {
  const url = URL.createObjectURL(new Blob([text], { type: `${type};charset=utf-8` }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

function Transcript({ segments, summary }: { segments: Segment[]; summary: string }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(toPlainText(segments));
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* trình duyệt từ chối clipboard: người dùng vẫn chọn và sao chép tay được */
    }
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle>Văn bản cuộc họp</CardTitle>
        <CardDescription>{summary}</CardDescription>
        <div className="col-start-2 row-span-2 row-start-1 flex flex-wrap items-start justify-self-end gap-2">
          <Button type="button" variant="outline" size="sm" onClick={copy} disabled={segments.length === 0}>
            {copied ? <Check /> : <Copy />}
            {copied ? "Đã chép" : "Sao chép"}
          </Button>
          <Button type="button" variant="outline" size="sm" disabled={segments.length === 0} onClick={() => save("cuoc-hop.txt", toPlainText(segments), "text/plain")}>
            <Download />
            .txt
          </Button>
          <Button type="button" variant="outline" size="sm" disabled={segments.length === 0} onClick={() => save("cuoc-hop.srt", toSrt(segments), "application/x-subrip")}>
            <Download />
            .srt
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {segments.length === 0 ? (
          <p className="text-sm text-muted-foreground">Không nghe ra lời nói nào trong file này.</p>
        ) : (
          <ol className="grid gap-2">
            {segments.map((s, i) => (
              <li key={i} className="grid grid-cols-[4.5rem_1fr] gap-3 text-sm">
                <span className="pt-0.5 text-right font-mono text-xs tabular-nums text-muted-foreground">{fmtClock(s.start)}</span>
                <span className="[overflow-wrap:anywhere]">
                  {s.speaker ? (
                    <Badge variant={s.speaker === "A" ? "default" : "secondary"} className="mr-2 align-middle">
                      Người {s.speaker}
                    </Badge>
                  ) : null}
                  {s.text}
                </span>
              </li>
            ))}
          </ol>
        )}
      </CardContent>
    </Card>
  );
}

function JobList({
  jobs,
  selectedId,
  deletingId,
  onOpen,
  onDelete,
}: {
  jobs: SttJob[];
  selectedId: string | null;
  deletingId: string | null;
  onOpen: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  const [confirming, setConfirming] = useState<SttJob | null>(null);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Job gần đây</CardTitle>
        <CardDescription>Văn bản được lưu 7 ngày, chỉ bạn xem được. File ghi âm bị xoá ngay khi chép xong.</CardDescription>
      </CardHeader>
      <CardContent>
        <ItemGroup>
          {jobs.map((j) => {
            const s = STATUS[j.status];
            return (
              <Item key={j.id} variant={j.id === selectedId ? "muted" : "outline"} size="sm">
                <ItemContent>
                  <ItemTitle className="flex-wrap">
                    <Badge variant={s.variant}>
                      {isActive(j.status) ? <Spinner className="motion-reduce:animate-none" data-icon="inline-start" /> : null}
                      {s.label}
                    </Badge>
                    <span className="tabular-nums">{j.durationS > 0 ? `${fmtClock(j.durationS)} âm thanh` : "Chưa biết thời lượng"}</span>
                  </ItemTitle>
                  <ItemDescription className="[overflow-wrap:anywhere]">
                    {fmtDateTime(j.createdAt)}
                    {j.error ? ` · ${j.error}` : ""}
                  </ItemDescription>
                </ItemContent>
                <ItemActions>
                  {j.status === "done" ? (
                    <Button type="button" variant="outline" size="sm" onClick={() => onOpen(j.id)}>
                      <Eye />
                      Xem
                    </Button>
                  ) : null}
                  <Button type="button" variant="ghost" size="icon-sm" aria-label="Xoá job" disabled={deletingId === j.id} onClick={() => setConfirming(j)}>
                    {deletingId === j.id ? <Spinner className="motion-reduce:animate-none" /> : <Trash2 />}
                  </Button>
                </ItemActions>
              </Item>
            );
          })}
        </ItemGroup>
      </CardContent>

      <AlertDialog open={confirming !== null} onOpenChange={(open) => !open && setConfirming(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogMedia className="bg-destructive/10 text-destructive">
              <Trash2 />
            </AlertDialogMedia>
            <AlertDialogTitle>Xoá job này?</AlertDialogTitle>
            <AlertDialogDescription>
              {confirming ? `Job lúc ${fmtDateTime(confirming.createdAt)} và văn bản kết quả sẽ bị xoá, không khôi phục được.` : null}
              {confirming && isActive(confirming.status) ? " Job đang chạy sẽ dừng." : null}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Giữ lại</AlertDialogCancel>
            <Button
              type="button"
              variant="destructive"
              onClick={() => {
                if (confirming) onDelete(confirming.id);
                setConfirming(null);
              }}
            >
              Xoá job
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  );
}

/**
 * Trang Ghi âm cuộc họp: tải file âm thanh/video lên, chạy nền (cuộc họp dài mất vài phút đến hàng chục phút), xem văn bản
 * có mốc thời gian, xuất .txt/.srt. KHÔNG tóm tắt, KHÔNG nạp vào kho tri thức (ADR-006). KHÔNG gồm sidebar / header.
 */
export function SttPage({ api }: { api: SttApi }) {
  const qc = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [fileKey, setFileKey] = useState(0);
  const [localError, setLocalError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const engines = useQuery({ queryKey: enginesKey, queryFn: () => api.engines(), retry: false });
  const engineDown = engines.data ? !engines.data.engines.find((e) => e.name === engines.data.default)?.available : false;

  const create = useMutation({
    mutationFn: (f: File) => api.createJob(f, { language: "vi" }),
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
    refetchInterval: (q) => (q.state.data?.some((j) => isActive(j.status)) ? 3000 : false),
  });
  const detail = useQuery({
    queryKey: jobKey(selectedId ?? ""),
    queryFn: () => api.getJob(selectedId!),
    enabled: selectedId !== null,
    refetchInterval: (q) => (q.state.data && isActive(q.state.data.status) ? 3000 : false),
  });

  function submit(e?: FormEvent) {
    e?.preventDefault();
    if (!file || create.isPending) return;
    if (file.size > MAX_MB * 1024 * 1024) return setLocalError(`File vượt giới hạn ${MAX_MB} MB.`);
    setLocalError(null);
    setSelectedId(null);
    create.reset();
    create.mutate(file);
    setFile(null);
    setFileKey((k) => k + 1);
  }

  const job = detail.data;
  const percent = job && job.durationS > 0 ? Math.min(100, Math.round((job.doneS / job.durationS) * 100)) : 0;

  return (
    <div className="w-full flex flex-col gap-4">
      <Card>
        <CardContent>
          <form onSubmit={submit} className="grid gap-4">
            <div className="grid gap-1.5">
              <Label htmlFor="stt-file">File ghi âm hoặc video cuộc họp</Label>
              <Input
                key={fileKey}
                id="stt-file"
                type="file"
                accept={ACCEPT}
                onChange={(e) => {
                  setFile(e.target.files?.[0] ?? null);
                  setLocalError(null);
                }}
                aria-describedby="stt-file-hint"
              />
              <p id="stt-file-hint" className="text-xs text-muted-foreground">
                MP3, WAV, M4A, MP4 và các định dạng thông dụng, tối đa {MAX_MB} MB và 3 giờ. Xử lý chạy nền, bạn có thể rời trang.
              </p>
            </div>
            <Button type="submit" size="lg" disabled={!file || create.isPending || engineDown} className="ml-auto h-10 px-4">
              {create.isPending ? <Spinner className="motion-reduce:animate-none" /> : <Mic />}
              Chuyển thành văn bản
            </Button>
          </form>
        </CardContent>
      </Card>

      {engineDown ? (
        <Alert>
          <TriangleAlert />
          <AlertTitle>Chưa có engine nhận dạng giọng nói</AlertTitle>
          <AlertDescription>Dịch vụ chuyển giọng nói chưa chạy trên máy chủ nên chưa gửi file được. Hãy báo quản trị viên.</AlertDescription>
        </Alert>
      ) : null}

      {localError || create.isError ? (
        <Alert variant="destructive">
          <TriangleAlert />
          <AlertTitle>Không gửi được</AlertTitle>
          <AlertDescription>{localError ?? errText(create.error)}</AlertDescription>
        </Alert>
      ) : null}

      {create.isPending ? (
        <Card aria-live="polite" aria-busy>
          <CardContent>
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <Spinner className="motion-reduce:animate-none" />
              Đang tải file lên… file lớn có thể mất vài phút. Đừng đóng trang.
            </p>
          </CardContent>
        </Card>
      ) : null}

      {selectedId && detail.isError ? (
        <Alert variant="destructive">
          <TriangleAlert />
          <AlertTitle>Không mở được job</AlertTitle>
          <AlertDescription>{errText(detail.error)}</AlertDescription>
        </Alert>
      ) : null}

      {job && isActive(job.status) ? (
        <Card aria-live="polite" aria-busy>
          <CardContent className="grid gap-3">
            <p className="text-sm font-medium">
              {job.status === "queued" || job.durationS === 0
                ? "Đang chờ tới lượt hoặc chuẩn bị file…"
                : `Đã chép ${fmtClock(job.doneS)} / ${fmtClock(job.durationS)} âm thanh (${percent}%)`}
            </p>
            <Progress value={percent} aria-label="Tiến độ chép lời" />
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

      {job?.status === "done" && job.segments ? (
        <Transcript segments={job.segments} summary={`${fmtClock(job.durationS)} âm thanh · engine ${job.engine} · lưu tới hết hạn`} />
      ) : null}

      {jobs.data && jobs.data.length > 0 ? (
        <JobList
          jobs={jobs.data}
          selectedId={selectedId}
          deletingId={remove.isPending ? (remove.variables ?? null) : null}
          onOpen={setSelectedId}
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
        File ghi âm bị xoá ngay khi chép xong, tên file không được lưu. Văn bản có thể sai (nhất là tên riêng và thuật ngữ): hãy nghe lại
        những chỗ quan trọng. Không tải lên cuộc họp mà bạn không được phép ghi lại.
      </p>
    </div>
  );
}
