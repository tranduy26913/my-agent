import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Copy, KeyRound, Lock, LockOpen, MoreHorizontal, TriangleAlert, UserPlus, Users } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogMedia,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { AccountState, AccountUser, UsersApi } from "../types";

const ALL = "all";
const usersKey = ["admin", "users"] as const;

const ACCOUNT_META: Record<AccountState, { label: string; cls: string }> = {
  active: { label: "Đang hoạt động", cls: "bg-success/10 text-success" },
  inactive: { label: "Đã khoá", cls: "bg-muted text-muted-foreground" },
  none: { label: "Chưa có tài khoản", cls: "border-border bg-transparent text-muted-foreground" },
  locked: { label: "Khoá tạm", cls: "bg-warning/10 text-warning" },
  other: { label: "Trạng thái khác", cls: "bg-warning/10 text-warning" },
};

const ROLE_LABEL: Record<string, string> = {
  employee: "Nhân viên",
  manager: "Quản lý",
  "truong-phong": "Trưởng phòng",
  hr: "Nhân sự",
  executive: "Ban điều hành",
  admin: "Quản trị",
};

type ActionKind = "create" | "deactivate" | "reactivate" | "reset";
interface Pending {
  kind: ActionKind;
  user: AccountUser;
}
interface Secret {
  name: string;
  email: string;
  password: string;
}

const COPY: Record<ActionKind, { title: (n: string) => string; body: (u: AccountUser) => string; confirm: string; destructive: boolean }> = {
  create: {
    title: (n) => `Tạo tài khoản cho ${n}?`,
    body: (u) =>
      `Tài khoản đăng nhập là ${u.email}. Hệ thống tạo một mật khẩu tạm và chỉ hiện nó một lần; người dùng bị buộc đổi mật khẩu ở lần đăng nhập đầu tiên.`,
    confirm: "Tạo tài khoản",
    destructive: false,
  },
  deactivate: {
    title: (n) => `Khoá tài khoản của ${n}?`,
    body: () => "Người này không đăng nhập được nữa cho tới khi bạn mở khoá. Dữ liệu của họ không bị xoá.",
    confirm: "Khoá tài khoản",
    destructive: true,
  },
  reactivate: {
    title: (n) => `Mở khoá tài khoản của ${n}?`,
    body: () => "Người này đăng nhập lại được bằng mật khẩu hiện có của họ.",
    confirm: "Mở khoá",
    destructive: false,
  },
  reset: {
    title: (n) => `Đặt lại mật khẩu của ${n}?`,
    body: () =>
      "Mật khẩu hiện tại không dùng được nữa. Hệ thống tạo một mật khẩu tạm, chỉ hiện một lần, và buộc đổi ở lần đăng nhập sau.",
    confirm: "Đặt lại mật khẩu",
    destructive: true,
  },
};

const errText = (e: unknown) => (e instanceof Error ? e.message : "Đã có lỗi xảy ra");

function actionsFor(u: AccountUser): ActionKind[] {
  if (u.account === "none") return u.employee?.active ? ["create"] : [];
  if (u.account === "active") return ["reset", "deactivate"];
  if (u.account === "inactive") return ["reactivate"];
  return []; // khoá tạm / trạng thái khác: chưa có thao tác an toàn đã kiểm chứng
}

const ACTION_ICON = { create: UserPlus, deactivate: Lock, reactivate: LockOpen, reset: KeyRound } as const;
const ACTION_LABEL: Record<ActionKind, string> = {
  create: "Tạo tài khoản",
  deactivate: "Khoá tài khoản",
  reactivate: "Mở khoá",
  reset: "Đặt lại mật khẩu",
};

/** Bỏ dấu và hạ chữ thường để ô tìm "nguyen" khớp "Nguyễn". */
const fold = (s: string) =>
  s
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/đ/gi, "d")
    .toLowerCase();

function CopyButton({ text }: { text: string }) {
  const [done, setDone] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setDone(true);
      setTimeout(() => setDone(false), 1500);
    } catch {
      /* clipboard bị từ chối: người dùng vẫn chọn và chép tay được */
    }
  }
  return (
    <Button type="button" variant="outline" onClick={copy} aria-label="Sao chép mật khẩu tạm">
      {done ? <Check /> : <Copy />}
      {done ? "Đã chép" : "Sao chép"}
    </Button>
  );
}

/**
 * Trang Tài khoản (admin): nhân viên ghép với tài khoản Zitadel. Tạo, khoá, mở khoá, đặt lại mật khẩu tạm.
 * Mật khẩu tạm chỉ hiện một lần trong hộp thoại, đóng được bằng nút (không đóng khi bấm ra ngoài hay Esc để khỏi mất).
 */
export function UsersPage({ api }: { api: UsersApi }) {
  const qc = useQueryClient();
  const users = useQuery({ queryKey: usersKey, queryFn: () => api.list() });
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState(ALL);
  const [dept, setDept] = useState(ALL);
  const [pending, setPending] = useState<Pending | null>(null);
  const [secret, setSecret] = useState<Secret | null>(null);

  const run = useMutation({
    mutationFn: async ({ kind, user }: Pending): Promise<string | null> => {
      switch (kind) {
        case "create":
          return (await api.create(user.email)).tempPassword;
        case "deactivate":
          await api.deactivate(user.zitadelId!);
          return null;
        case "reactivate":
          await api.reactivate(user.zitadelId!);
          return null;
        case "reset":
          return api.resetPassword(user.zitadelId!);
      }
    },
    onSuccess: (password, { user }) => {
      void qc.invalidateQueries({ queryKey: usersKey });
      setPending(null);
      if (password) setSecret({ name: user.fullName, email: user.email, password });
    },
  });

  const items = useMemo(() => users.data ?? [], [users.data]);
  const needsAttention = (u: AccountUser) => u.warning !== null || u.account === "locked" || u.account === "other";
  const counts = useMemo(
    () => ({
      active: items.filter((u) => u.account === "active").length,
      inactive: items.filter((u) => u.account === "inactive").length,
      none: items.filter((u) => u.account === "none" && u.employee?.active).length,
      attention: items.filter(needsAttention).length,
    }),
    [items],
  );
  const departments = useMemo(
    () => [...new Set(items.map((u) => u.employee?.department).filter((d): d is string => !!d))].sort(),
    [items],
  );

  const shown = useMemo(() => {
    const needle = fold(search.trim());
    return items.filter((u) => {
      if (status === "attention" ? !needsAttention(u) : status !== ALL && u.account !== status) return false;
      if (dept !== ALL && u.employee?.department !== dept) return false;
      if (!needle) return true;
      return fold(`${u.fullName} ${u.email} ${u.employee?.code ?? ""}`).includes(needle);
    });
  }, [items, search, status, dept]);

  const filtered = search.trim() !== "" || status !== ALL || dept !== ALL;

  function ask(kind: ActionKind, user: AccountUser) {
    run.reset();
    setPending({ kind, user });
  }

  return (
    <div className="flex flex-col gap-4 text-foreground">
      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Tìm theo tên, email hoặc mã nhân viên"
          aria-label="Tìm tài khoản"
          className="bg-card sm:w-72"
        />
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="w-full bg-card sm:w-56" aria-label="Trạng thái tài khoản">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Mọi trạng thái ({items.length})</SelectItem>
            <SelectItem value="active">Đang hoạt động ({counts.active})</SelectItem>
            <SelectItem value="none">Chưa có tài khoản ({counts.none})</SelectItem>
            <SelectItem value="inactive">Đã khoá ({counts.inactive})</SelectItem>
            <SelectItem value="attention">Cần xem lại ({counts.attention})</SelectItem>
          </SelectContent>
        </Select>
        <Select value={dept} onValueChange={setDept}>
          <SelectTrigger className="w-full bg-card sm:w-44" aria-label="Phòng ban">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Mọi phòng ban</SelectItem>
            {departments.map((d) => (
              <SelectItem key={d} value={d}>
                {d}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {users.error ? (
        <Alert variant="destructive" className="flex items-center gap-3 border-0 bg-destructive/10 px-4 py-3">
          <TriangleAlert className="size-4 shrink-0" />
          <p className="min-w-0 flex-1 text-sm">{errText(users.error)}</p>
          <Button type="button" variant="link" size="sm" onClick={() => users.refetch()} className="h-auto shrink-0 p-0 text-destructive">
            Thử lại
          </Button>
        </Alert>
      ) : null}

      <Card className="gap-0 overflow-hidden py-0">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="pl-4">Nhân viên</TableHead>
              <TableHead className="hidden w-32 sm:table-cell">Phòng ban</TableHead>
              <TableHead className="hidden w-64 lg:table-cell">Vai trò</TableHead>
              <TableHead className="w-36 sm:w-44">Tài khoản</TableHead>
              <TableHead className="w-14 pr-4">
                <span className="sr-only">Thao tác</span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users.isLoading
              ? Array.from({ length: 6 }, (_, i) => (
                  <TableRow key={i} className="hover:bg-transparent">
                    <TableCell className="pl-4" colSpan={5}>
                      <Skeleton className="h-5 w-full" />
                    </TableCell>
                  </TableRow>
                ))
              : shown.map((u) => {
                  const meta = ACCOUNT_META[u.account];
                  const acts = actionsFor(u);
                  return (
                    <TableRow key={u.key}>
                      <TableCell className="min-w-36 whitespace-normal pl-4">
                        <p className="flex flex-wrap items-center gap-x-2 text-sm font-medium">
                          {u.fullName || u.email}
                          {u.employee && !u.employee.active ? (
                            <Badge variant="outline" className="font-normal text-muted-foreground">
                              Đã nghỉ việc
                            </Badge>
                          ) : null}
                        </p>
                        <p className="break-all text-xs text-muted-foreground">{u.email}</p>
                        <p className="text-xs text-muted-foreground sm:hidden">{u.employee?.department}</p>
                        {u.warning ? (
                          <p className="mt-1 flex items-start gap-1 text-xs text-warning">
                            <TriangleAlert className="mt-0.5 size-3 shrink-0" />
                            {u.warning}
                          </p>
                        ) : null}
                      </TableCell>
                      <TableCell className="hidden sm:table-cell">{u.employee?.department ?? "—"}</TableCell>
                      <TableCell className="hidden whitespace-normal lg:table-cell">
                        <div className="flex flex-wrap gap-1">
                          {u.employee?.roles.map((r) => (
                            <Badge key={r} variant="secondary" className="font-normal">
                              {ROLE_LABEL[r] ?? r}
                            </Badge>
                          )) ?? "—"}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary" className={meta.cls}>
                          {meta.label}
                        </Badge>
                      </TableCell>
                      <TableCell className="pr-4">
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button type="button" variant="ghost" size="icon" disabled={acts.length === 0} aria-label={`Thao tác cho ${u.fullName || u.email}`}>
                              <MoreHorizontal />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end" className="w-52">
                            {acts.map((k) => {
                              const Icon = ACTION_ICON[k];
                              return (
                                <DropdownMenuItem key={k} variant={COPY[k].destructive && k === "deactivate" ? "destructive" : "default"} onSelect={() => ask(k, u)}>
                                  <Icon />
                                  {ACTION_LABEL[k]}
                                </DropdownMenuItem>
                              );
                            })}
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  );
                })}
          </TableBody>
        </Table>

        {!users.isLoading && !users.error && shown.length === 0 ? (
          <Empty className="border-0 py-10">
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <Users />
              </EmptyMedia>
              <EmptyTitle className="text-base">{filtered ? "Không có ai khớp bộ lọc" : "Chưa có nhân viên nào"}</EmptyTitle>
              <EmptyDescription>
                {filtered ? "Thử bỏ bớt điều kiện lọc." : "Danh bạ nhân sự đang trống: nạp danh bạ trước khi tạo tài khoản."}
              </EmptyDescription>
            </EmptyHeader>
          </Empty>
        ) : null}
      </Card>

      <p className="text-xs text-muted-foreground">
        Mọi thao tác ở trang này được ghi vào Nhật ký (ai làm, với tài khoản nào, lúc nào); mật khẩu tạm thì không bao giờ được ghi lại.
        Quyền trong portal vẫn lấy từ danh bạ nhân sự, nên khoá tài khoản không thay đổi trạng thái nhân viên.
      </p>

      {pending ? (
        <AlertDialog open onOpenChange={(open) => !open && !run.isPending && setPending(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogMedia className={COPY[pending.kind].destructive ? "bg-destructive/10 text-destructive" : "bg-primary/10 text-primary"}>
                {(() => {
                  const Icon = ACTION_ICON[pending.kind];
                  return <Icon />;
                })()}
              </AlertDialogMedia>
              <AlertDialogTitle>{COPY[pending.kind].title(pending.user.fullName || pending.user.email)}</AlertDialogTitle>
              <AlertDialogDescription asChild>
                <div className="grid gap-2">
                  <p>{COPY[pending.kind].body(pending.user)}</p>
                  <p className="text-xs">Việc này được ghi vào Nhật ký.</p>
                  {run.isError ? (
                    <Alert variant="destructive">
                      <TriangleAlert />
                      <AlertDescription>{errText(run.error)}</AlertDescription>
                    </Alert>
                  ) : null}
                </div>
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <Button type="button" variant="secondary" disabled={run.isPending} onClick={() => setPending(null)}>
                Huỷ
              </Button>
              <Button
                type="button"
                variant={COPY[pending.kind].destructive ? "destructive" : "default"}
                disabled={run.isPending}
                onClick={() => run.mutate(pending)}
              >
                {run.isPending ? <Spinner /> : null}
                {COPY[pending.kind].confirm}
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      ) : null}

      {secret ? (
        <AlertDialog open>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogMedia className="bg-success/10 text-success">
                <KeyRound />
              </AlertDialogMedia>
              <AlertDialogTitle>Mật khẩu tạm của {secret.name}</AlertDialogTitle>
              <AlertDialogDescription asChild>
                <div className="grid gap-3">
                  <p>
                    Đăng nhập bằng <span className="font-medium text-foreground">{secret.email}</span>. Họ bị buộc đổi mật khẩu ở lần đăng nhập đầu tiên.
                  </p>
                  <div className="flex gap-2">
                    <Input readOnly value={secret.password} aria-label="Mật khẩu tạm" className="bg-muted font-mono" onFocus={(e) => e.currentTarget.select()} />
                    <CopyButton text={secret.password} />
                  </div>
                  <p className="text-xs">
                    Mật khẩu này chỉ hiện một lần và không được lưu ở đâu cả. Gửi cho họ qua kênh riêng, đừng đăng vào nhóm chat chung.
                  </p>
                </div>
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <Button type="button" onClick={() => setSecret(null)}>
                Đã lưu lại, đóng
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      ) : null}
    </div>
  );
}
