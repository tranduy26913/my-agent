import { useState } from "react";
import { Eye, Trash2 } from "lucide-react";
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
import { Item, ItemActions, ItemContent, ItemDescription, ItemGroup, ItemTitle } from "@/components/ui/item";
import { Spinner } from "@/components/ui/spinner";
import type { JobStatus, OcrJob } from "../types";

const STATUS: Record<JobStatus, { label: string; variant: "secondary" | "outline" | "destructive" | "default" }> = {
  queued: { label: "Đang chờ", variant: "outline" },
  running: { label: "Đang đọc", variant: "secondary" },
  done: { label: "Xong", variant: "default" },
  failed: { label: "Lỗi", variant: "destructive" },
};

export const fmtDateTime = (iso: string) =>
  new Date(iso).toLocaleString("vi-VN", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });

interface Props {
  jobs: OcrJob[];
  selectedId: string | null;
  deletingId: string | null;
  onOpen: (id: string) => void;
  onDelete: (id: string) => void;
}

/** Các job PDF gần đây của chính người dùng (backend giữ 7 ngày). */
export function JobList({ jobs, selectedId, deletingId, onOpen, onDelete }: Props) {
  const [confirming, setConfirming] = useState<OcrJob | null>(null);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Job gần đây</CardTitle>
        <CardDescription>Kết quả PDF được lưu 7 ngày, chỉ bạn xem được. Ảnh đọc trực tiếp nên không lưu.</CardDescription>
      </CardHeader>
      <CardContent>
        <ItemGroup>
          {jobs.map((j) => {
            const s = STATUS[j.status];
            const active = j.status === "queued" || j.status === "running";
            return (
              <Item key={j.id} variant={j.id === selectedId ? "muted" : "outline"} size="sm">
                <ItemContent>
                  <ItemTitle className="flex-wrap">
                    <Badge variant={s.variant}>
                      {active ? <Spinner className="motion-reduce:animate-none" data-icon="inline-start" /> : null}
                      {s.label}
                    </Badge>
                    <span className="tabular-nums">
                      {j.pagesTotal > 0 ? `${j.pagesDone}/${j.pagesTotal} trang` : "Chưa biết số trang"}
                    </span>
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
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    aria-label="Xoá job"
                    disabled={deletingId === j.id}
                    onClick={() => setConfirming(j)}
                  >
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
              {confirming && (confirming.status === "queued" || confirming.status === "running") ? " Job đang chạy sẽ dừng." : null}
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
