import { useRef, useState, type DragEvent } from "react";
import { CircleAlert, CircleCheck, File as FileIcon, FileImage, FileText, Upload, X } from "lucide-react";
import { useKbHost } from "../host";
import { useDocuments, useKbMutations } from "../hooks";
import { ACCEPT, MAX_FILE_BYTES, fileKindOf, inspectFile } from "../files";
import { fmtSize } from "../format";
import { DEPARTMENTS, DOC_TYPES, ROLES, VISIBILITY_META } from "../labels";
import type { UploadMeta, Visibility } from "../types";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { Drawer } from "./Drawer";
import { Field, ToggleChip } from "./ui";

/** Radix Select không cho SelectItem có value rỗng, nên "không chọn" dùng giá trị này. */
const NONE = "__none__";

type ItemState = "ready" | "needs-info" | "uploading" | "done" | "failed" | "rejected";

interface Item {
  id: string;
  file: File;
  state: ItemState;
  needsMeta: boolean;
  progress: number;
  message?: string;
}

interface FormState {
  title: string;
  docType: string;
  department: string;
  visibility: Visibility | "";
  depts: string[];
  roles: string[];
  classified: boolean;
  effectiveFrom: string;
  supersedes: string;
}

const EMPTY_FORM: FormState = {
  title: "",
  docType: "",
  department: "",
  visibility: "",
  depts: [],
  roles: [],
  classified: false,
  effectiveFrom: "",
  supersedes: "",
};

let seq = 0;
const nextId = () => `u${++seq}`;
const toggle = (list: string[], v: string) => (list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);

/** Cắt giữa, giữ đuôi: "bien-ban-hop-giao-ban…kinh-doanh.pdf" */
function MiddleTruncate({ name }: { name: string }) {
  const long = name.length > 28;
  const head = long ? name.slice(0, name.length - 14) : name;
  const tail = long ? name.slice(-14) : "";
  return (
    <p className="flex min-w-0 flex-1 text-sm font-medium" title={long ? name : undefined}>
      <span className="truncate">{head}</span>
      {tail ? <span className="shrink-0">{tail}</span> : null}
    </p>
  );
}

interface Props {
  open: boolean;
  onClose: () => void;
}

export function UploadPanel({ open, onClose }: Props) {
  const { api } = useKbHost();
  const { data: existing } = useDocuments();
  const { refresh } = useKbMutations();

  const [items, setItems] = useState<Item[]>([]);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [dragging, setDragging] = useState(false);
  const [running, setRunning] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Mở lại panel thì bắt đầu một phiên nạp mới
  const [wasOpen, setWasOpen] = useState(open);
  if (open !== wasOpen) {
    setWasOpen(open);
    if (open) {
      setItems([]);
      setForm(EMPTY_FORM);
      setRunning(false);
    }
  }

  const patch = (id: string, p: Partial<Item>) => setItems((cur) => cur.map((it) => (it.id === id ? { ...it, ...p } : it)));
  const set = <K extends keyof FormState>(k: K, v: FormState[K]) => setForm((f) => ({ ...f, [k]: v }));

  async function addFiles(list: FileList | File[]) {
    const incoming = await Promise.all(
      [...list].map(async (file): Promise<Item> => {
        const check = await inspectFile(file);
        if (!check.ok) return { id: nextId(), file, state: "rejected", needsMeta: false, progress: 0, message: check.reason };
        return { id: nextId(), file, state: check.hasFrontmatter ? "ready" : "needs-info", needsMeta: !check.hasFrontmatter, progress: 0 };
      }),
    );
    setItems((cur) => [...cur, ...incoming]);
  }

  function onDrop(e: DragEvent<HTMLLabelElement>) {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files.length) void addFiles(e.dataTransfer.files);
  }

  const pending = items.filter((i) => i.state === "ready" || i.state === "needs-info" || i.state === "failed");
  const needInfo = pending.filter((i) => i.needsMeta);
  const showForm = needInfo.length > 0 && !running;

  const scopeNeedsList = form.visibility === "phong-ban" || form.visibility === "han-che";
  const formValid =
    !showForm ||
    (form.docType !== "" &&
      form.department !== "" &&
      form.visibility !== "" &&
      (!scopeNeedsList || form.depts.length + form.roles.length > 0));
  const allDone = items.length > 0 && pending.length === 0 && items.some((i) => i.state === "done");

  function buildMeta(): UploadMeta {
    return {
      title: form.title.trim() || undefined,
      docType: form.docType,
      department: form.department,
      visibility: form.visibility as Visibility,
      allowedDepartments: scopeNeedsList ? form.depts : [],
      allowedRoles: scopeNeedsList ? form.roles : [],
      classified: form.classified,
      effectiveFrom: form.effectiveFrom || undefined,
      supersedes: form.supersedes || null,
    };
  }

  async function submit() {
    setRunning(true);
    const meta = buildMeta();
    for (const it of pending) {
      patch(it.id, { state: "uploading", progress: 0, message: undefined });
      try {
        await api.uploadDocument(it.file, it.needsMeta ? meta : null, (p) => patch(it.id, { progress: p }));
        patch(it.id, { state: "done", progress: 100 });
      } catch (err) {
        patch(it.id, { state: "failed", message: err instanceof Error ? err.message : "Mất kết nối mạng" });
      }
    }
    setRunning(false);
    await refresh();
  }

  const footerLabel = running ? "Đang nạp…" : `Nạp ${pending.length} tài liệu`;

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title="Nạp tài liệu"
      subtitle="Tệp Markdown có frontmatter đầy đủ thì không phải điền gì thêm"
      footer={
        allDone ? (
          <Button type="button" size="lg" onClick={onClose} className="min-h-10 px-4">Xong</Button>
        ) : (
          <>
            <Button type="button" size="lg" variant="secondary" onClick={onClose} className="min-h-10 px-4">Huỷ</Button>
            <Button type="button" size="lg" disabled={running || pending.length === 0 || !formValid} onClick={submit} className="min-h-10 px-4">
              {footerLabel}
            </Button>
          </>
        )
      }
    >
      <div className="flex-1 overflow-y-auto px-6 pb-6 pt-2">
        <label
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          className={cn(
            "flex cursor-pointer flex-col items-center rounded-xl border border-dashed px-6 py-8 text-center transition-colors",
            dragging ? "border-foreground/40 bg-background" : "border-input bg-background/60 hover:bg-background",
          )}
        >
          <input
            ref={inputRef}
            type="file"
            multiple
            accept={ACCEPT}
            className="sr-only"
            onChange={(e) => { if (e.target.files) void addFiles(e.target.files); e.target.value = ""; }}
          />
          <p className="text-sm font-medium [@media(hover:none)]:hidden">{dragging ? "Thả tệp để tải lên" : "Kéo thả tài liệu vào đây"}</p>
          <p className="mt-1 text-pretty text-sm text-muted-foreground">Markdown, PDF, Word, ảnh scan JPG hoặc PNG. Tối đa {MAX_FILE_BYTES / 1024 / 1024} MB mỗi tệp</p>
          <span className="mt-4 inline-flex h-9 items-center gap-1.5 rounded-lg border bg-background px-3 text-sm font-medium"><Upload className="size-4" />Chọn tệp</span>
        </label>

        {items.length > 0 ? (
          <ul className="mt-4 divide-y divide-border">
            {items.map((it) => {
              const kind = fileKindOf(it.file.name);
              const Icon = kind === "image" ? FileImage : kind === "other" ? FileIcon : FileText;
              const canRemove = it.state !== "done" && it.state !== "uploading";
              return (
                <li key={it.id} className="flex items-center gap-3 py-3">
                  <Icon className="size-5 shrink-0 text-muted-foreground" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-baseline gap-3">
                      <MiddleTruncate name={it.file.name} />
                      {it.state === "uploading" ? <p className="shrink-0 text-sm tabular-nums text-muted-foreground">{it.progress}%</p> : null}
                    </div>
                    <div className="mt-1 flex min-h-5 items-center gap-1.5 text-xs text-muted-foreground">
                      {it.state === "uploading" ? (
                        <Progress value={it.progress} aria-label={`Đang tải ${it.file.name}`} className="h-1 w-full" />
                      ) : it.state === "done" ? (
                        <><CircleCheck className="size-3.5 text-success" />Đã nạp, đang xử lý · {fmtSize(it.file.size)}</>
                      ) : it.state === "ready" ? (
                        <><CircleCheck className="size-3.5 text-success" />Đủ thông tin từ frontmatter · {fmtSize(it.file.size)}</>
                      ) : it.state === "needs-info" ? (
                        <span className="inline-flex items-center gap-1.5 text-warning"><CircleAlert className="size-3.5" />Cần điền thông tin bên dưới · {fmtSize(it.file.size)}</span>
                      ) : (
                        <>
                          <span className="text-destructive">{it.message}</span>
                          {it.state === "failed" ? (
                            <>
                              <span aria-hidden>·</span>
                              <Button type="button" variant="link" onClick={submit} className="h-auto p-0 text-xs text-foreground">Thử lại</Button>
                            </>
                          ) : null}
                        </>
                      )}
                    </div>
                  </div>
                  <div className="flex w-8 shrink-0 justify-end">
                    {canRemove ? (
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        aria-label={`Bỏ tệp ${it.file.name}`}
                        onClick={() => setItems((cur) => cur.filter((x) => x.id !== it.id))}
                        className="text-muted-foreground"
                      >
                        <X />
                      </Button>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ul>
        ) : null}

        {showForm ? (
          <div className="mt-6 border-t border-border pt-6">
            <h3 className="text-sm font-semibold">
              Thông tin cho {needInfo.length === 1 ? needInfo[0].file.name : `${needInfo.length} tệp chưa có thông tin`}
            </h3>
            <p className="mt-1 text-sm text-muted-foreground">Trợ lý dùng các trường này để lọc quyền và trích dẫn nguồn</p>

            <div className="mt-5 grid gap-4">
              <Field label="Tiêu đề" htmlFor="kb-title" hint={needInfo.length > 1 ? "Để trống thì lấy theo tên từng tệp" : undefined}>
                <Input id="kb-title" value={form.title} onChange={(e) => set("title", e.target.value)} placeholder="Để trống thì lấy theo tên tệp" className="h-10" />
              </Field>

              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Loại văn bản" required htmlFor="kb-type">
                  <Select value={form.docType} onValueChange={(v) => set("docType", v)}>
                    <SelectTrigger id="kb-type" className="h-10 w-full"><SelectValue placeholder="Chọn loại" /></SelectTrigger>
                    <SelectContent>
                      {DOC_TYPES.map((t) => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </Field>
                <Field label="Phòng sở hữu" required htmlFor="kb-dept">
                  <Select value={form.department} onValueChange={(v) => set("department", v)}>
                    <SelectTrigger id="kb-dept" className="h-10 w-full"><SelectValue placeholder="Chọn phòng" /></SelectTrigger>
                    <SelectContent>
                      {DEPARTMENTS.map((d) => <SelectItem key={d} value={d}>{d}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </Field>
              </div>

              <fieldset className="grid gap-2">
                <legend className="mb-1.5 text-sm font-medium">Ai được xem <span className="text-destructive">*</span></legend>
                <RadioGroup value={form.visibility} onValueChange={(v) => set("visibility", v as Visibility)} className="gap-2">
                  {(Object.keys(VISIBILITY_META) as Visibility[]).map((v) => {
                    const meta = VISIBILITY_META[v];
                    const on = form.visibility === v;
                    return (
                      <Label
                        key={v}
                        htmlFor={`kb-vis-${v}`}
                        className={cn("flex cursor-pointer items-start gap-3 rounded-xl border p-3 font-normal", on ? "border-primary ring-2 ring-primary/15" : "hover:bg-muted/50")}
                      >
                        <RadioGroupItem id={`kb-vis-${v}`} value={v} className="mt-0.5" />
                        <span>
                          <span className="block text-sm font-medium">{meta.label}</span>
                          <span className="block text-xs text-muted-foreground">{meta.hint}</span>
                        </span>
                      </Label>
                    );
                  })}
                </RadioGroup>
              </fieldset>

              {scopeNeedsList ? (
                <>
                  <Field label="Phòng được xem">
                    <div className="flex flex-wrap gap-1.5">
                      {DEPARTMENTS.map((d) => <ToggleChip key={d} on={form.depts.includes(d)} onToggle={() => set("depts", toggle(form.depts, d))}>{d}</ToggleChip>)}
                    </div>
                  </Field>
                  <Field
                    label="Vai trò được xem"
                    hint={form.depts.length + form.roles.length === 0 ? "Chọn ít nhất một phòng hoặc một vai trò, nếu không sẽ không ai xem được" : undefined}
                  >
                    <div className="flex flex-wrap gap-1.5">
                      {ROLES.map((r) => <ToggleChip key={r.value} on={form.roles.includes(r.value)} onToggle={() => set("roles", toggle(form.roles, r.value))}>{r.label}</ToggleChip>)}
                    </div>
                  </Field>
                </>
              ) : null}

              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Hiệu lực từ" htmlFor="kb-from">
                  <Input id="kb-from" type="date" value={form.effectiveFrom} onChange={(e) => set("effectiveFrom", e.target.value)} className="h-10" />
                </Field>
                <Field label="Thay thế văn bản" htmlFor="kb-sup">
                  <Select value={form.supersedes || NONE} onValueChange={(v) => set("supersedes", v === NONE ? "" : v)}>
                    <SelectTrigger id="kb-sup" className="h-10 w-full"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value={NONE}>Không thay thế</SelectItem>
                      {(existing ?? []).filter((d) => !d.supersededBy).map((d) => <SelectItem key={d.docId} value={d.docId}>{d.docId} · {d.title}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </Field>
              </div>

              <Label htmlFor="kb-classified" className="cursor-pointer items-start gap-3 font-normal">
                <Checkbox id="kb-classified" checked={form.classified} onCheckedChange={(v) => set("classified", v === true)} className="mt-0.5" />
                <span>
                  <span className="block text-sm font-medium">Văn bản Mật</span>
                  <span className="block text-xs text-muted-foreground">Chỉ xử lý trên máy chủ nội bộ, không gửi ra dịch vụ OCR bên ngoài</span>
                </span>
              </Label>
            </div>
          </div>
        ) : null}
      </div>
    </Drawer>
  );
}
