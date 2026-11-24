import { useEffect, useState, type FormEvent, type KeyboardEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { Lock, SearchX, Send, TriangleAlert } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Item, ItemContent, ItemGroup, ItemMedia, ItemTitle } from "@/components/ui/item";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import type { AskRequest, AskResult, LookupApi } from "../types";

const MAX_LEN = 1000;

/** Câu hỏi mẫu, để người mới biết hỏi kiểu gì. Bám đúng các văn bản có trong kho demo. */
const SUGGESTIONS = [
  "Nhân viên chính thức được nghỉ phép năm mấy ngày?",
  "Công tác phí đi tỉnh được thanh toán những khoản nào?",
  "Quy trình mua sắm trên 50 triệu cần ai duyệt?",
  "Giờ làm việc và quy định đi muộn như thế nào?",
];

interface Turn {
  id: number;
  req: AskRequest;
  result: AskResult;
}

const fmtDate = (iso: string) => iso.split("-").reverse().join("/");
const fmtSeconds = (ms: number) => `${(ms / 1000).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} giây`;

/** Đếm giây đã chờ trong lúc model trả lời (vài chục giây với model local), để người dùng biết hệ thống vẫn chạy. */
function useElapsed(active: boolean) {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    if (!active) return;
    const t0 = Date.now();
    const timer = setInterval(() => setSeconds(Math.floor((Date.now() - t0) / 1000)), 1000);
    return () => {
      clearInterval(timer);
      setSeconds(0);
    };
  }, [active]);
  return seconds;
}

/** Biến "[1]" trong câu trả lời thành nhãn nhỏ, khớp với danh sách Nguồn bên dưới. */
function AnswerText({ text }: { text: string }) {
  const parts = text.split(/(\[\d+\])/g);
  return (
    <p className="whitespace-pre-line text-sm/7">
      {parts.map((part, i) => {
        const m = /^\[(\d+)\]$/.exec(part);
        return m ? (
          <Badge key={i} variant="secondary" className="mx-0.5 h-4 rounded px-1 align-baseline text-[0.7rem] tabular-nums text-primary-ink">
            {m[1]}
          </Badge>
        ) : (
          <span key={i}>{part}</span>
        );
      })}
    </p>
  );
}

function ResultCard({ turn }: { turn: Turn }) {
  const { req, result } = turn;
  return (
    <Card>
      <CardContent className="grid gap-4">
        <div>
          <p className="text-sm font-medium">{req.question}</p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Theo quy định tại ngày {fmtDate(result.asOf)} · {fmtSeconds(result.latencyMs)} · {result.model}
          </p>
        </div>

        {result.found ? (
          <AnswerText text={result.answer} />
        ) : (
          <Alert>
            <SearchX />
            <AlertTitle>Không tìm thấy</AlertTitle>
            <AlertDescription>{result.answer}</AlertDescription>
          </Alert>
        )}

        {result.citations.length > 0 ? (
          <div>
            <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Nguồn</h3>
            <ItemGroup className="gap-0">
              {result.citations.map((c) => (
                <Item key={c.n} size="xs" className="items-start px-0 py-1">
                  <ItemMedia>
                    <Badge variant="secondary" className="h-4 rounded px-1 text-[0.7rem] tabular-nums text-primary-ink">
                      {c.n}
                    </Badge>
                  </ItemMedia>
                  <ItemContent>
                    <ItemTitle className="min-w-0 font-normal [overflow-wrap:anywhere]">{c.label}</ItemTitle>
                  </ItemContent>
                </Item>
              ))}
            </ItemGroup>
          </div>
        ) : null}

        {result.withheld.length > 0 ? (
          <Alert>
            <Lock />
            <AlertTitle>Có thể còn thông tin trong tài liệu Mật</AlertTitle>
            <AlertDescription>
              <p>
                Bạn được xem các văn bản này, nhưng theo CTA-CS-007 Điều 5 nội dung Mật không được gửi tới mô hình AI nên trợ lý
                không đọc phần đó. Hãy mở bản gốc:
              </p>
              <ul className="mt-1 list-disc pl-5">
                {result.withheld.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        ) : null}
      </CardContent>
    </Card>
  );
}

/**
 * Trang Tra cứu: hỏi đáp về quy chế nội bộ, câu trả lời có trích dẫn nguồn, tra được theo quy định tại một ngày.
 * KHÔNG gồm sidebar / header: đó là khung của portal (src/shell). Lịch sử chỉ giữ trong phiên làm việc này.
 */
export function LookupPage({ api }: { api: LookupApi }) {
  const [question, setQuestion] = useState("");
  const [asOf, setAsOf] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);

  const ask = useMutation({
    mutationFn: (req: AskRequest) => api.ask(req),
    onSuccess: (result, req) => setTurns((cur) => [{ id: Date.now(), req, result }, ...cur]),
  });
  const waited = useElapsed(ask.isPending);

  const trimmed = question.trim();
  const canSend = trimmed.length > 0 && !ask.isPending;

  function submit(e?: FormEvent) {
    e?.preventDefault();
    if (!canSend) return;
    ask.mutate({ question: trimmed, asOf: asOf || undefined });
    setQuestion("");
  }

  // Enter gửi, Shift+Enter xuống dòng. Bỏ qua Enter khi đang gõ tiếng Việt bằng bộ gõ (IME đang soạn).
  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) submit(e);
  }

  return (
    <div className="w-full flex flex-col gap-4">
      <Card>
        <CardContent>
          <form onSubmit={submit} className="grid gap-3">
            <Label htmlFor="lookup-question" className="sr-only">
              Câu hỏi
            </Label>
            <Textarea
              id="lookup-question"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={onKeyDown}
              maxLength={MAX_LEN}
              rows={3}
              placeholder="Hỏi về quy chế, quy trình, chính sách nội bộ. Ví dụ: Nhân viên mới được nghỉ phép mấy ngày?"
              className="min-h-20 resize-none text-sm"
            />
            <div className="flex flex-wrap items-end gap-3">
              <div className="grid gap-1.5">
                <Label htmlFor="lookup-asof" className="text-xs font-normal text-muted-foreground">
                  Tra theo quy định tại ngày (để trống là hôm nay)
                </Label>
                <Input id="lookup-asof" type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)} className="h-9 w-44" />
              </div>
              <div className="ml-auto flex items-center gap-3">
                {question.length > MAX_LEN * 0.9 ? (
                  <span className="text-xs tabular-nums text-muted-foreground">
                    {question.length}/{MAX_LEN}
                  </span>
                ) : null}
                <Button type="submit" size="lg" disabled={!canSend} className="h-10 px-4">
                  {ask.isPending ? <Spinner className="motion-reduce:animate-none" /> : <Send />}
                  Hỏi
                </Button>
              </div>
            </div>
          </form>

          {turns.length === 0 && !ask.isPending ? (
            <div className="mt-4">
              <Separator className="mb-4" />
              <p className="mb-2 text-xs text-muted-foreground">Thử hỏi:</p>
              <div className="flex flex-wrap gap-2">
                {SUGGESTIONS.map((s) => (
                  <Button key={s} type="button" variant="outline" size="sm" className="h-auto whitespace-normal py-1.5 text-left" onClick={() => setQuestion(s)}>
                    {s}
                  </Button>
                ))}
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>

      {ask.isPending ? (
        <Card aria-live="polite" aria-busy>
          <CardContent className="grid gap-3">
            <p className="text-sm font-medium">{ask.variables?.question}</p>
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <Spinner className="motion-reduce:animate-none" />
              Đang tra cứu tài liệu… {waited > 0 ? `${waited} giây` : null}
              {waited >= 15 ? " (lần đầu có thể mất khoảng một phút)" : null}
            </p>
          </CardContent>
        </Card>
      ) : null}

      {ask.isError && !ask.isPending ? (
        <Alert variant="destructive">
          <TriangleAlert />
          <AlertTitle>Không tra cứu được</AlertTitle>
          <AlertDescription>
            <p>{ask.error instanceof Error ? ask.error.message : "Đã có lỗi xảy ra"}</p>
            {ask.variables ? (
              <Button type="button" variant="link" size="sm" className="mt-1 h-auto p-0 text-destructive" onClick={() => ask.mutate(ask.variables)}>
                Thử lại
              </Button>
            ) : null}
          </AlertDescription>
        </Alert>
      ) : null}

      {turns.map((t) => (
        <ResultCard key={t.id} turn={t} />
      ))}

      <p className="text-center text-xs text-muted-foreground">
        Trợ lý chỉ trả lời dựa trên tài liệu bạn được phép xem. Câu hỏi được ghi nhật ký để kiểm soát chất lượng và quyền truy cập.
      </p>
    </div>
  );
}
