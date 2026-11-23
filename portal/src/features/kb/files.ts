import type { FileKind } from "./types";

export const MAX_FILE_BYTES = 25 * 1024 * 1024;
export const ACCEPT = ".md,.pdf,.docx,.png,.jpg,.jpeg";

export function fileKindOf(name: string): FileKind {
  const ext = name.split(".").pop()?.toLowerCase() ?? "";
  if (ext === "md") return "md";
  if (ext === "pdf") return "pdf";
  if (ext === "docx") return "docx";
  if (["png", "jpg", "jpeg"].includes(ext)) return "image";
  return "other";
}

export type Inspection =
  | { ok: true; hasFrontmatter: boolean }
  | { ok: false; reason: string };

/**
 * Kiểm tra sơ bộ trước khi gửi. Backend vẫn kiểm lại (không tin client).
 * Tệp Markdown bắt đầu bằng "---" và có `doc_id:` thì coi là đã đủ thông tin.
 */
export async function inspectFile(file: File): Promise<Inspection> {
  const kind = fileKindOf(file.name);
  if (kind === "other") {
    const ext = file.name.includes(".") ? `.${file.name.split(".").pop()}` : "này";
    return { ok: false, reason: `Không nhận tệp ${ext}. Dùng Markdown, PDF, Word hoặc ảnh` };
  }
  if (file.size > MAX_FILE_BYTES) {
    return { ok: false, reason: "Quá 25 MB" };
  }
  if (kind !== "md") return { ok: true, hasFrontmatter: false };
  const head = (await file.slice(0, 2000).text()).replace(/^﻿/, "");
  const hasFrontmatter = head.startsWith("---") && /^doc_id:/m.test(head);
  return { ok: true, hasFrontmatter };
}
