import type { UsageApi, UsageGroup, UsageReport } from "../types";

const g = (key: string, name: string, calls: number, inp: number, out: number, cost: number, department = ""): UsageGroup => ({
  key,
  name,
  department,
  calls,
  inputTokens: inp,
  outputTokens: out,
  costUsd: cost,
});

const thisMonth = () => new Date().toISOString().slice(0, 7);

/** Dữ liệu giả để làm giao diện khi chưa có backend. */
export function createMockUsageApi(delayMs = 400): UsageApi {
  return {
    async report(month) {
      await new Promise((r) => setTimeout(r, delayMs));
      const m = month || thisMonth();
      const report: UsageReport = {
        month: m,
        months: [m],
        calls: 61,
        inputTokens: 184_200,
        outputTokens: 33_900,
        costUsd: 22.14,
        budgetUsdPerUser: 20,
        byUser: [
          g("e5", "Đỗ Quang Huy", 24, 90_000, 16_000, 21.4, "CNTT"),
          g("e12", "Lê Văn Bình", 19, 52_000, 9_500, 0.74, "KD"),
          g("e8", "Phạm Thị Hà", 12, 30_000, 6_000, 0, "HCNS"),
          g("u3", "Người dùng #3", 6, 12_200, 2_400, 0, "CNTT"),
        ],
        byModel: [g("claude-sonnet-5-5", "claude-sonnet-5-5", 14, 60_000, 12_000, 22.14), g("local:qwen3-4b", "local:qwen3-4b", 47, 124_200, 21_900, 0)],
        byPurpose: [g("rag", "rag", 55, 170_000, 31_000, 22.14), g("ocr", "ocr", 6, 14_200, 2_900, 0)],
        byDay: [g("d1", `${m}-21`, 18, 50_000, 9_000, 7.2), g("d2", `${m}-22`, 25, 70_000, 12_900, 9.9), g("d3", `${m}-23`, 18, 64_200, 12_000, 5.04)],
      };
      return report;
    },
  };
}
