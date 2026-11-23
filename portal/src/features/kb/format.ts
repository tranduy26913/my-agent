/** "2026-01-01" → "01/01/2026" */
export function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  const [y, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${y}`;
}

/** Cùng năm hiện tại thì bỏ năm: "14/11 09:42" */
export function fmtDateTime(iso: string): string {
  const date = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  const base = `${pad(date.getDate())}/${pad(date.getMonth() + 1)}`;
  const year = date.getFullYear() === new Date().getFullYear() ? "" : `/${date.getFullYear()}`;
  return `${base}${year} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function fmtSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1).replace(".", ",")} MB`;
}

/** Bỏ dấu + thường hoá, để gõ "nghi phep" vẫn khớp "Nghỉ phép" (giống f_unaccent ở backend). */
export function fold(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase();
}
