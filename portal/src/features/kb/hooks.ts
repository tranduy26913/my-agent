import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useKbHost } from "./host";

/*
 * Chỉ dùng phần API của TanStack Query có ở CẢ v4 (LibreChat) lẫn v5 (portal):
 * cú pháp object, data / isLoading / error, invalidateQueries({ queryKey }).
 * Không dùng isPending (v5 only), không truyền hàm vào refetchInterval. Dùng isBusy() cho mutation.
 */

export const kbKeys = {
  all: ["kb"] as const,
  list: ["kb", "documents"] as const,
  detail: (docId: string) => ["kb", "documents", docId] as const,
};

export function useDocuments() {
  const { api } = useKbHost();
  const [polling, setPolling] = useState(false);
  const query = useQuery({
    queryKey: kbKeys.list,
    queryFn: () => api.listDocuments(),
    refetchInterval: polling ? 2000 : false,
  });
  // Còn tài liệu đang xử lý thì tự làm mới danh sách để thấy nó chuyển sang Sẵn sàng / Lỗi
  const shouldPoll = !!query.data?.some((d) => d.status === "processing");
  if (shouldPoll !== polling) setPolling(shouldPoll);
  return query;
}

export function useDocument(docId: string | null) {
  const { api } = useKbHost();
  return useQuery({
    queryKey: kbKeys.detail(docId ?? ""),
    queryFn: () => api.getDocument(docId as string),
    enabled: !!docId,
  });
}

export function useKbMutations() {
  const { api } = useKbHost();
  const queryClient = useQueryClient();
  const refresh = () => queryClient.invalidateQueries({ queryKey: kbKeys.all });

  // onSettled (không phải onSuccess): thao tác hàng loạt thật có thể xong một phần rồi báo lỗi (HTTP 207);
  // dù thành công hay lỗi cũng tải lại để danh sách phản ánh đúng những gì đã đổi.
  const reindex = useMutation({ mutationFn: (ids: string[]) => api.reindex(ids), onSettled: refresh });
  const remove = useMutation({ mutationFn: (ids: string[]) => api.deleteDocuments(ids), onSettled: refresh });
  const quarantine = useMutation({
    mutationFn: (v: { docId: string; on: boolean }) => api.setQuarantine(v.docId, v.on),
    onSettled: refresh,
  });
  return { reindex, remove, quarantine, refresh };
}

/**
 * Mutation đang chạy? v4 gọi trạng thái này là "loading", v5 gọi là "pending",
 * và cờ isLoading / isPending cũng khác tên giữa hai bản. So theo status để chạy được ở cả hai.
 */
export function isBusy(mutation: { status: string }): boolean {
  return mutation.status === "loading" || mutation.status === "pending";
}
