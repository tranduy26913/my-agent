import { LogIn, RefreshCw } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { LOOP_TEXT, METRICS, RISKS, ROLES } from "../data";
import { RoadmapBoard } from "./roadmap-board";

/** Trang công khai /roadmap: không gọi API, không đọc phiên đăng nhập. */
export function RoadmapPage() {
  return (
    <main className="mx-auto flex max-w-[1360px] flex-col gap-9 px-4 pt-6 pb-16 sm:px-6">
      <div className="flex items-center justify-between gap-4">
        <span className="text-sm font-medium">Trợ lý số Công ty A</span>
        <Button asChild variant="outline" size="sm">
          {/* Mô-đun giao diện không import Next.js nên dùng thẻ a thường; /login là trang đầy đủ, không cần client routing. */}
          <a href="/login">
            <LogIn />
            Đăng nhập portal
          </a>
        </Button>
      </div>

      <header className="flex max-w-[800px] flex-col gap-3.5">
        <Badge variant="secondary" className="w-fit tracking-wider uppercase">
          Kế hoạch triển khai · Bản đề xuất
        </Badge>
        <h1 className="text-[clamp(28px,4vw,40px)] leading-[1.15] font-extrabold tracking-tight text-balance">
          Lộ trình đưa AI vào doanh nghiệp
        </h1>
        <p className="text-muted-foreground max-w-[70ch] text-base">
          Đọc từ trên xuống theo giai đoạn. Mỗi cột là một làn công việc, mũi tên cho biết đầu ra của bước này là đầu vào của
          bước nào. Đường đậm là mạch chính, đường gạch đỏ là cổng phải duyệt trước khi sang giai đoạn sau.
        </p>
      </header>

      <RoadmapBoard />

      <Alert>
        <RefreshCw />
        <AlertDescription className="text-sm">
          <strong className="text-foreground">{LOOP_TEXT.lead}</strong> {LOOP_TEXT.body}
        </AlertDescription>
      </Alert>

      <section className="flex flex-col gap-4">
        <h2 className="text-[22px] font-bold tracking-tight">{METRICS.title}</h2>
        <p className="text-muted-foreground max-w-[70ch]">{METRICS.intro}</p>
        <Card className="py-0">
          <Table className="min-w-[720px] text-[13.5px]">
            <TableHeader>
              <TableRow>
                <TableHead>Nhóm</TableHead>
                <TableHead>Chỉ số</TableHead>
                <TableHead>Nguồn số liệu</TableHead>
                <TableHead>Dùng ở</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {METRICS.rows.map((r) => (
                <TableRow key={r.group}>
                  <TableCell className="font-semibold whitespace-nowrap">{r.group}</TableCell>
                  <TableCell className="whitespace-normal">{r.metric}</TableCell>
                  <TableCell className="text-muted-foreground font-mono text-xs">{r.source}</TableCell>
                  <TableCell>{r.usedIn}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
        <p className="text-muted-foreground text-[12.5px]">{METRICS.note}</p>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-[22px] font-bold tracking-tight">{ROLES.title}</h2>
        <div className="grid grid-cols-[repeat(auto-fit,minmax(260px,1fr))] gap-3">
          {ROLES.items.map((r) => (
            <Card key={r.title} size="sm" className="border">
              <CardHeader>
                <CardTitle className="text-[14.5px] font-bold">{r.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground text-[13.5px]">{r.text}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-[22px] font-bold tracking-tight">{RISKS.title}</h2>
        <div className="grid grid-cols-[repeat(auto-fit,minmax(260px,1fr))] gap-3">
          {RISKS.items.map((r) => (
            <Card key={r.title} size="sm" className="border">
              <CardHeader>
                <CardTitle className="text-[14.5px] font-bold">{r.title}</CardTitle>
                <CardDescription className="text-[13.5px]">{r.text}</CardDescription>
              </CardHeader>
              <CardContent>
                <span className="text-muted-foreground font-mono text-[11.5px]">Kiểm soát: {r.control}</span>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>
    </main>
  );
}
