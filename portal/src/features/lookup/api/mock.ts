import type { AskResult, LookupApi } from "../types";

const today = () => new Date().toISOString().slice(0, 10);

/** Dữ liệu giả để làm giao diện khi chưa có backend. Có hai ca: tìm thấy và không tìm thấy. */
export function createMockLookupApi(delayMs = 1500): LookupApi {
  return {
    async ask({ question, asOf }) {
      await new Promise((r) => setTimeout(r, delayMs));
      const base = { asOf: asOf ?? today(), model: "mock", latencyMs: delayMs, withheld: [] as string[] };
      if (/phép/i.test(question)) {
        return {
          ...base,
          found: true,
          answer:
            "Nhân viên chính thức được nghỉ phép năm 12 ngày làm việc mỗi năm [1]. Thâm niên từ 5 năm trở lên được cộng thêm 1 ngày cho mỗi 5 năm [1].",
          citations: [{ n: 1, label: "CTA-QC-003 – Điều 3: Số ngày phép", docId: "CTA-QC-003" }],
        } satisfies AskResult;
      }
      return {
        ...base,
        found: false,
        answer: "Không tìm thấy thông tin này trong các tài liệu nội bộ mà bạn được phép xem.",
        citations: [],
      } satisfies AskResult;
    },
  };
}
