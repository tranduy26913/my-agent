import type { AuditApi, AuditItem } from "../types";

const LABELS: Record<string, string> = {
  kb_upload: "Nạp tài liệu vào kho",
  kb_reindex: "Nạp lại tài liệu",
  kb_quarantine: "Cách ly tài liệu",
  kb_delete: "Gỡ tài liệu khỏi kho",
  kb_view_classified: "Xem nội dung tài liệu Mật",
  tool_denied: "Công cụ bị từ chối",
  rag_ask: "Tra cứu quy chế",
  rag_error: "Tra cứu lỗi",
};

function at(minutesAgo: number): string {
  return new Date(Date.now() - minutesAgo * 60_000).toISOString();
}

const ALL: AuditItem[] = [
  { id: 12, ts: at(4), event: "kb_view_classified", actor: "huy.do@cty-a.example", label: LABELS.kb_view_classified, summary: "CTA-CS-007", highlight: "alert", detail: { doc_id: "CTA-CS-007", chunks: 9 } },
  { id: 11, ts: at(18), event: "rag_ask", actor: "binh.le@cty-a.example", label: LABELS.rag_ask, summary: "Có câu trả lời", highlight: null, detail: { found: true, model: "local:qwen3-4b", latency_ms: 21400 } },
  { id: 10, ts: at(35), event: "tool_denied", actor: "mai.ngo@cty-a.example", label: LABELS.tool_denied, summary: "hr_lookup", highlight: "alert", detail: { tool: "hr_lookup", step: 1 } },
  { id: 9, ts: at(90), event: "kb_quarantine", actor: "huy.do@cty-a.example", label: LABELS.kb_quarantine, summary: "Cách ly CTA-QC-009", highlight: "warn", detail: { doc_id: "CTA-QC-009", on: true } },
  { id: 8, ts: at(130), event: "rag_error", actor: "ha.pham@cty-a.example", label: LABELS.rag_error, summary: "Model local không phản hồi", highlight: "warn", detail: { error: "Model local không phản hồi", latency_ms: 120000 } },
  { id: 7, ts: at(60 * 26), event: "kb_upload", actor: "huy.do@cty-a.example", label: LABELS.kb_upload, summary: "CTA-QC-012", highlight: null, detail: { doc_id: "CTA-QC-012", kind: "md", chunks: 14 } },
  { id: 6, ts: at(60 * 27), event: "kb_reindex", actor: "huy.do@cty-a.example", label: LABELS.kb_reindex, summary: "CTA-QC-003", highlight: null, detail: { doc_id: "CTA-QC-003", chunks: 11 } },
  { id: 5, ts: at(60 * 50), event: "rag_ask", actor: "duc.hoang@cty-a.example", label: LABELS.rag_ask, summary: "Không tìm thấy trong tài liệu được xem", highlight: null, detail: { found: false, model: "local:qwen3-4b" } },
  { id: 4, ts: at(60 * 51), event: "kb_delete", actor: "khoa.dang@cty-a.example", label: LABELS.kb_delete, summary: "CTA-QC-001", highlight: "warn", detail: { doc_id: "CTA-QC-001", chunks: 6, classified: false } },
];

/** Dữ liệu giả để làm giao diện khi chưa có backend. Lọc và phân trang (3 dòng/trang) như backend thật. */
export function createMockAuditApi(delayMs = 400, pageSize = 3): AuditApi {
  return {
    async list(q, cursor) {
      await new Promise((r) => setTimeout(r, delayMs));
      const needle = q.actor.trim().toLowerCase();
      const rows = ALL.filter(
        (i) =>
          (!q.event || i.event === q.event) &&
          (!needle || i.actor.toLowerCase().includes(needle)) &&
          (!q.since || i.ts.slice(0, 10) >= q.since) &&
          (!q.until || i.ts.slice(0, 10) <= q.until) &&
          (!cursor || i.id < cursor),
      );
      const items = rows.slice(0, pageSize);
      const eventCounts: Record<string, number> = {};
      ALL.forEach((i) => {
        eventCounts[i.event] = (eventCounts[i.event] ?? 0) + 1;
      });
      return {
        items,
        nextCursor: rows.length > pageSize ? items[items.length - 1].id : null,
        eventCounts,
        eventLabels: LABELS,
      };
    },
  };
}
