import type { ReactNode } from "react";
import { Trash2 } from "lucide-react";
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogMedia,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";

interface ConfirmDialogProps {
  title: string;
  /** Hậu quả cụ thể, có tên đối tượng */
  children: ReactNode;
  confirmLabel: string;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * Hộp xác nhận việc nguy hiểm (xoá), dựng trên AlertDialog của shadcn. Tiêu đề là câu hỏi, nút nói đúng việc.
 * Dùng Button thường thay AlertDialogAction: bên gọi tự đóng hộp sau khi việc xong (hoặc lỗi), không đóng ngay khi bấm.
 */
export function ConfirmDialog({ title, children, confirmLabel, busy, onConfirm, onCancel }: ConfirmDialogProps) {
  return (
    <AlertDialog open onOpenChange={(open) => !open && onCancel()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogMedia className="bg-destructive/10 text-destructive">
            <Trash2 />
          </AlertDialogMedia>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div>{children}</div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <Button type="button" variant="secondary" onClick={onCancel}>Huỷ</Button>
          <Button type="button" variant="destructive" onClick={onConfirm} disabled={busy}>{confirmLabel}</Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
