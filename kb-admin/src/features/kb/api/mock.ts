import type {
  AccessCheck,
  KbApi,
  KbChunk,
  KbDocument,
  KbDocumentDetail,
  KbHistoryEntry,
  UploadMeta,
  Visibility,
} from "../types";
import { fileKindOf } from "../files";

/*
 * Bản cài DỮ LIỆU GIẢ để làm giao diện khi backend chưa có endpoint.
 * Tên, số hiệu, phòng, phạm vi xem lấy từ frontmatter thật trong data/knowledge.
 * Trạng thái xử lý, số đoạn, người nạp, nội dung đoạn là BỊA.
 */

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function doc(p: Partial<KbDocument> & Pick<KbDocument, "docId" | "title" | "department">): KbDocument {
  return {
    soHieu: null,
    docType: null,
    fileKind: "md",
    visibility: "cong-khai",
    allowedDepartments: [],
    allowedRoles: [],
    classified: false,
    effectiveFrom: null,
    effectiveTo: null,
    supersedes: null,
    supersededBy: null,
    version: "1",
    status: "ready",
    chunkCount: 24,
    ocrPages: 0,
    source: `data/knowledge/${p.docId}.md`,
    uploadedBy: "Trần Thị Lan",
    createdAt: "2026-11-14T09:42:00+07:00",
    ...p,
  };
}

let store: KbDocument[] = [
  doc({ docId: "SVT-QC-003", soHieu: "01/2026/QĐ-SVT", title: "Quy chế nghỉ phép (bản 2026)", docType: "quy-che", department: "HCNS", effectiveFrom: "2026-01-01", supersedes: "SVT-QC-002", version: "2", chunkCount: 38 }),
  doc({ docId: "SVT-QC-002", soHieu: "12/2023/QĐ-SVT", title: "Quy chế nghỉ phép (bản 2024)", docType: "quy-che", department: "HCNS", effectiveFrom: "2024-01-01", effectiveTo: "2026-01-01", supersededBy: "SVT-QC-003", chunkCount: 33 }),
  doc({ docId: "SVT-QC-004", soHieu: "02/2026/QĐ-SVT", title: "Quy chế tiền lương, thưởng và phụ cấp", docType: "quy-che", department: "HCNS", visibility: "han-che", allowedDepartments: ["HCNS", "BGD"], allowedRoles: ["hr", "executive"], classified: true, effectiveFrom: "2026-02-01", chunkCount: 41 }),
  doc({ docId: "SVT-DA-011", soHieu: "DA-2026-07/CHARTER", title: "Điều lệ dự án Cổng dịch vụ khách hàng Phương Nam (PNC Portal)", docType: "ho-so-du-an", department: "DA", visibility: "phong-ban", allowedDepartments: ["DA", "KD", "BGD"], classified: true, effectiveFrom: "2026-05-25", chunkCount: 29 }),
  doc({ docId: "SVT-TB-018", title: "SVT-TB-018-dieu-chinh-gio-lam-viec.pdf", docType: "thong-bao", department: "HCNS", fileKind: "pdf", status: "processing", statusNote: "Đang OCR trang 2 / 3", chunkCount: 0, ocrPages: 3, source: "data/scan/SVT-TB-018-dieu-chinh-gio-lam-viec.pdf" }),
  doc({ docId: "CTP-NV017", title: "de-nghi-thanh-toan-CTP-NV017.png", docType: "chung-tu", department: "TCKT", fileKind: "image", visibility: "phong-ban", allowedDepartments: ["TCKT", "BGD"], status: "error", statusNote: "OCR không đọc được bảng số tiền", chunkCount: 0, ocrPages: 1, source: "data/scan/de-nghi-thanh-toan-CTP-NV017.png" }),
  doc({ docId: "SVT-TL-099", soHieu: "21/2026/TB-SVT", title: "Thông báo lịch nghỉ Tết Dương lịch 2027", docType: "thong-bao", department: "HCNS", effectiveFrom: "2026-11-15", effectiveTo: "2027-01-05", status: "quarantined", statusNote: "Có câu ra lệnh cho trợ lý", chunkCount: 6 }),
  doc({ docId: "SVT-DA-012", soHieu: "DA-2026-07/BBH-01", title: "Biên bản họp khởi động dự án PNC Portal", docType: "bien-ban-hop", department: "DA", visibility: "phong-ban", allowedDepartments: ["DA", "BGD"], effectiveFrom: "2026-06-05", chunkCount: 14 }),
  doc({ docId: "SVT-QT-010", soHieu: "02/2026/QT-SVT", title: "Quy trình tuyển dụng", docType: "quy-trinh", department: "HCNS", visibility: "phong-ban", allowedDepartments: ["HCNS", "BGD"], allowedRoles: ["manager"], effectiveFrom: "2026-01-15", chunkCount: 22 }),
  doc({ docId: "SVT-QT-006", soHieu: "03/2026/QT-SVT", title: "Quy trình mua sắm và thanh toán nội bộ", docType: "quy-trinh", department: "TCKT", visibility: "phong-ban", allowedDepartments: ["TCKT", "BGD"], effectiveFrom: "2026-03-01", chunkCount: 27 }),
  doc({ docId: "SVT-CS-007", soHieu: "04/2026/CS-SVT", title: "Chính sách an toàn thông tin và sử dụng trí tuệ nhân tạo", docType: "chinh-sach", department: "CNTT", effectiveFrom: "2026-03-01", chunkCount: 31 }),
  doc({ docId: "SVT-FAQ-013", soHieu: "FAQ-HCNS-2026", title: "Hỏi đáp nhân sự thường gặp", docType: "hoi-dap", department: "HCNS", effectiveFrom: "2026-03-15", version: "4", chunkCount: 19 }),
  doc({ docId: "SVT-HD-009", soHieu: "HD-HCNS-2026-02", title: "Sổ tay hội nhập nhân viên mới", docType: "huong-dan", department: "HCNS", effectiveFrom: "2026-03-01", version: "2", chunkCount: 26 }),
  doc({ docId: "SVT-HD-008", soHieu: "HD-CNTT-2026-01", title: "Hướng dẫn sử dụng dịch vụ CNTT", docType: "huong-dan", department: "CNTT", effectiveFrom: "2026-01-05", version: "3", chunkCount: 21 }),
  doc({ docId: "SVT-QD-005", soHieu: "08/2025/QĐ-SVT", title: "Quy định về chế độ công tác phí", docType: "quy-dinh", department: "TCKT", effectiveFrom: "2025-09-01", chunkCount: 17 }),
  doc({ docId: "SVT-QC-001", soHieu: "05/2025/QĐ-SVT", title: "Nội quy lao động", docType: "noi-quy", department: "HCNS", effectiveFrom: "2025-07-01", chunkCount: 28 }),
];

const history = new Map<string, KbHistoryEntry[]>();
function log(docId: string, by: string, text: string) {
  history.set(docId, [{ at: new Date().toISOString(), by, text }, ...(history.get(docId) ?? [])]);
}

const SECTIONS = [
  "Chương I > Điều 1. Phạm vi điều chỉnh",
  "Chương I > Điều 2. Đối tượng áp dụng",
  "Chương II > Điều 5. Nguyên tắc chung",
  "Chương II > Điều 6. Trách nhiệm của các bên",
  "Chương III > Điều 9. Điều khoản thi hành",
];

function makeChunks(d: KbDocument): KbChunk[] {
  if (d.chunkCount === 0) return [];
  return SECTIONS.slice(0, Math.min(5, d.chunkCount)).map((section, i) => ({
    ordinal: i + 1,
    page: d.fileKind === "md" ? null : i + 1,
    section,
    content: `[Nội dung mẫu] Đoạn ${i + 1} của "${d.title}". Khi nối API thật, đây là nội dung đoạn đã được cắt và index.`,
  }));
}

function detailOf(d: KbDocument): KbDocumentDetail {
  const base: KbHistoryEntry[] = [{ at: d.createdAt, by: d.uploadedBy ?? "—", text: `Nạp lần đầu, ${d.chunkCount} đoạn` }];
  return { ...d, chunks: makeChunks(d), history: [...(history.get(d.docId) ?? []), ...base], accessLogged: d.classified };
}

/* Quy tắc giống can_read() ở backend/app/rag/acl.py */
interface Principal { name: string; department: string; roles: string[]; active: boolean }
const PEOPLE: Record<string, Principal> = {
  "lan@saoviet.vn": { name: "Trần Thị Lan", department: "HCNS", roles: ["hr"], active: true },
  "minh@saoviet.vn": { name: "Lê Quang Minh", department: "TCKT", roles: [], active: true },
  "long@saoviet.vn": { name: "Phạm Đức Long", department: "BGD", roles: ["executive"], active: true },
  "cu@saoviet.vn": { name: "Hoàng Văn Cũ", department: "KD", roles: [], active: false },
};

function canRead(p: Principal, v: Visibility, depts: string[], roles: string[]): { allowed: boolean; reason: string } {
  if (!p.active) return { allowed: false, reason: "Nhân viên đã nghỉ việc, không xem được tài liệu nào" };
  const inDept = depts.includes(p.department);
  const hasRole = p.roles.some((r) => roles.includes(r));
  if (v === "cong-khai") return { allowed: true, reason: "Văn bản công khai, mọi nhân viên đang làm việc đều xem được" };
  if (v === "phong-ban") {
    return inDept || hasRole
      ? { allowed: true, reason: inDept ? `Thuộc phòng ${p.department} được xem` : "Có vai trò được xem" }
      : { allowed: false, reason: `Phòng ${p.department} và vai trò của người này đều không nằm trong danh sách được xem` };
  }
  if (depts.length === 0 && roles.length === 0) {
    return { allowed: false, reason: "Văn bản hạn chế nhưng chưa khai báo phòng hay vai trò nào: cấu hình lỗi nên không ai xem được" };
  }
  const deptOk = inDept || depts.length === 0;
  const roleOk = hasRole || roles.length === 0;
  if (deptOk && roleOk) return { allowed: true, reason: "Thoả cả điều kiện phòng ban và vai trò" };
  return { allowed: false, reason: `Văn bản hạn chế cần thoả cả phòng ban và vai trò; người này thiếu ${!deptOk ? "phòng ban phù hợp" : "vai trò phù hợp"}` };
}

export function createMockKbApi(): KbApi {
  return {
    async listDocuments() {
      await sleep(250);
      return structuredClone(store);
    },

    async getDocument(docId) {
      await sleep(200);
      const found = store.find((d) => d.docId === docId);
      if (!found) throw new Error("Không tìm thấy tài liệu");
      return structuredClone(detailOf(found));
    },

    async uploadDocument(file, meta: UploadMeta | null, onProgress) {
      for (let p = 0; p <= 100; p += 20) {
        onProgress(p);
        await sleep(160);
      }
      const kind = fileKindOf(file.name);
      const stem = file.name.replace(/\.[^.]+$/, "");
      const created = doc({
        docId: stem.match(/^[A-Z]+-[A-Z]+-\d+/)?.[0] ?? `DOC-${Date.now().toString(36).toUpperCase()}`,
        title: meta?.title?.trim() || stem.replace(/[-_]+/g, " "),
        department: meta?.department ?? "HCNS",
        docType: meta?.docType ?? null,
        visibility: meta?.visibility ?? "cong-khai",
        allowedDepartments: meta?.allowedDepartments ?? [],
        allowedRoles: meta?.allowedRoles ?? [],
        classified: meta?.classified ?? false,
        effectiveFrom: meta?.effectiveFrom || null,
        supersedes: meta?.supersedes ?? null,
        fileKind: kind,
        status: "processing",
        statusNote: kind === "md" ? "Đang cắt đoạn và tạo vector" : "Đang OCR",
        chunkCount: 0,
        source: file.name,
        createdAt: new Date().toISOString(),
      });
      store = [created, ...store.filter((d) => d.docId !== created.docId)];
      log(created.docId, "Bạn", "Nạp tài liệu");
      // Giả lập xử lý nền: 3 giây sau chuyển sang Sẵn sàng
      setTimeout(() => {
        store = store.map((d) =>
          d.docId === created.docId ? { ...d, status: "ready", statusNote: undefined, chunkCount: 18 } : d,
        );
      }, 3000);
      return structuredClone(created);
    },

    async reindex(docIds) {
      await sleep(300);
      store = store.map((d) => (docIds.includes(d.docId) ? { ...d, status: "processing", statusNote: "Đang nạp lại" } : d));
      docIds.forEach((id) => log(id, "Bạn", "Nạp lại"));
      setTimeout(() => {
        store = store.map((d) => (docIds.includes(d.docId) && d.status === "processing" ? { ...d, status: "ready", statusNote: undefined } : d));
      }, 2500);
    },

    async setQuarantine(docId, on) {
      await sleep(250);
      store = store.map((d) =>
        d.docId === docId
          ? { ...d, status: on ? "quarantined" : "ready", statusNote: on ? "Cách ly thủ công" : undefined }
          : d,
      );
      log(docId, "Bạn", on ? "Cách ly: trợ lý không tra cứu được" : "Bỏ cách ly");
    },

    async deleteDocuments(docIds) {
      await sleep(300);
      store = store.filter((d) => !docIds.includes(d.docId));
    },

    async checkAccess(docId, email): Promise<AccessCheck> {
      await sleep(250);
      const found = store.find((d) => d.docId === docId);
      const person = PEOPLE[email.trim().toLowerCase()];
      if (!found) throw new Error("Không tìm thấy tài liệu");
      if (!person) return { allowed: false, reason: "Không tìm thấy nhân viên với email này", person: null };
      return { ...canRead(person, found.visibility, found.allowedDepartments, found.allowedRoles), person: person.name };
    },
  };
}
